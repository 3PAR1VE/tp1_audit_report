import datetime
import locale

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools import pytz


class AuditReportWizard(models.TransientModel):
    _name = "tp1_audit_report.audit_report_wizard"

    date = fields.Date(required=True, default=datetime.datetime.now().date())
    journal_id = fields.Many2one(comodel_name="account.journal", required=True, domain=[('type', '=', 'bank')])

    def generate_report(self):
        current_user_id = self.env.user.id
        tz = pytz.timezone(self.env.user.tz) or pytz.utc
        locale.setlocale(locale.LC_ALL, self.env.user.lang)
        data = {
            'date': self.date.strftime("%d/%m/%Y"),
            'user_name': None,
            'report_date': pytz.utc.localize(datetime.datetime.now()).astimezone(tz).strftime("%d/%m/%Y %H:%M:%S"),
            'company_name': self.env.company.name
        }

        domain = [
            ('date', '=', self.date),
            ('journal_id', '=', self.journal_id.id),
            ('move_type', '=', 'entry'),
            ('state', '=', 'posted')
        ]

        moves = self.env['account.move'].search(domain)

        if not moves:
            raise UserError(_("No journal entries found"))

        moves_list = []

        report_total = 0
        report_total_ref = 0

        for move in moves:
            if not move.partner_id:
                continue
            amount = move.amount_total_signed
            amount_ref = next((l.credit_usd for l in move.line_ids if l.credit_usd > 0), 0)
            moves_list.append({
                'company_name': move.partner_id.name,
                'memo': move.ref,
                'amount': f"Bs {locale.format('%.2f', round(amount,2), True)}",
                'amount_ref': f"$ {locale.format('%.2f', round(amount_ref,2), True)}"
            })
            report_total += amount
            report_total_ref += amount_ref

        data = {
            'date': self.date.strftime("%d/%m/%Y"),
            'journal_name': self.journal_id.name,
            'report_date': pytz.utc.localize(datetime.datetime.now()).astimezone(tz).strftime("%d/%m/%Y %H:%M:%S"),
            'company_name': self.env.company.name,
            'moves': moves_list,
            'report_total': f"Bs {locale.format('%.2f', round(report_total,2), True)}",
            'report_total_ref': f"$ {locale.format('%.2f', round(report_total_ref, 2), True)}"
        }

        report = self.env.ref('tp1_audit_report.audit_report_action')

        return report.report_action(self, data=data)

    def _get_report_base_filename(self):

        tz = pytz.timezone(self.env.user.tz) or pytz.utc

        name = f"audit_{self.date.strftime('%d%m%Y')}"

        return f"{name}_{pytz.utc.localize(datetime.datetime.now()).astimezone(tz).strftime('%d%m%Y_%H%M%S')}"

