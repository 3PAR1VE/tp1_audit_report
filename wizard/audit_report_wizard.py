import datetime
import locale
import logging

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools import pytz

_logger = logging.getLogger(__name__)


class AuditReportWizard(models.TransientModel):
    _name = "tp1_audit_report.audit_report_wizard"

    date = fields.Date(required=True, default=datetime.datetime.now().date())
    journal_id = fields.Many2one(comodel_name="account.journal", required=True, domain=[('type', '=', 'bank')])

    def generate_report(self):
        current_user_id = self.env.user.id
        tz = pytz.timezone(self.env.user.tz) or pytz.utc
        _logger.info(f"LANGUAGE IS: '{self.env.user.lang}'")
        locale.setlocale(locale.LC_ALL, '')

        data = {
            'date': self.date.strftime("%d/%m/%Y"),
            'user_name': None,
            'report_date': pytz.utc.localize(datetime.datetime.now()).astimezone(tz).strftime("%d/%m/%Y %H:%M:%S"),
            'company_name': self.env.company.name
        }

        payments = self.env['account.payment'].search([
            ('date', '=', self.date),
            ('journal_id', '=', self.journal_id.id),
            ('state', '=', 'posted')
        ])

        if not payments:
            raise UserError(_("No journal entries found"))

        report_payments = []

        report_total = 0
        report_total_ref = 0

        for payment in payments:
            if not payment.partner_id:
                continue
            report_payments.append({
                'company_name': payment.partner_id.name,
                'memo': payment.ref,
                'amount': f"Bs {locale.format_string('%.2f', round(payment.amount,2), True)}",
                'amount_ref': f"$ {locale.format_string('%.2f', round(payment.amount/payment.tax_today,2), True)}"
            })
            report_total += payment.amount
            report_total_ref += payment.amount/payment.tax_today

        data = {
            'date': self.date.strftime("%d/%m/%Y"),
            'journal_name': self.journal_id.name,
            'report_date': pytz.utc.localize(datetime.datetime.now()).astimezone(tz).strftime("%d/%m/%Y %H:%M:%S"),
            'company_name': self.env.company.name,
            'moves': report_payments,
            'report_total': f"Bs {locale.format_string('%.2f', round(report_total,2), True)}",
            'report_total_ref': f"$ {locale.format_string('%.2f', round(report_total_ref, 2), True)}"
        }

        report = self.env.ref('tp1_audit_report.audit_report_action')

        return report.report_action(self, data=data)

    def _get_report_base_filename(self):

        tz = pytz.timezone(self.env.user.tz) or pytz.utc

        name = f"audit_{self.date.strftime('%d%m%Y')}"

        return f"{name}_{pytz.utc.localize(datetime.datetime.now()).astimezone(tz).strftime('%d%m%Y_%H%M%S')}"

