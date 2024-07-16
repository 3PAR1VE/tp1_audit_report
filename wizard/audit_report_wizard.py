import datetime

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
        data = {
            'date': self.date.strftime("%d/%m/%Y"),
            'user_name': None,
            'report_date': pytz.utc.localize(datetime.datetime.now()).astimezone(tz).strftime("%d/%m/%Y %H:%M:%S"),
            'company_name': self.env.company.name
        }

        domain = [
            ('date', '=', self.date),
            ('journal_id', '=', self.journal_id.id),
            ('move_type', '=', 'entry')
        ]

        moves = self.env['account.move'].search(domain)

        if not moves:
            raise UserError(_("No journal entries found"))

        moves_list = []

        for move in moves:
            if not move.partner_id:
                continue
            moves_list.append({
                'company_name': move.partner_id.name,
                'memo': move.ref,
                'amount': f"Bs {move.amount_total_signed}",
                'amount_ref': f"$ {next((l.credit_usd for l in move.line_ids if l.credit_usd > 0), 0)}"
            })

        data = {
            'date': self.date.strftime("%d/%m/%Y"),
            'journal_name': self.journal_id.name,
            'report_date': pytz.utc.localize(datetime.datetime.now()).astimezone(tz).strftime("%d/%m/%Y %H:%M:%S"),
            'company_name': self.env.company.name,
            'moves': moves_list
        }

        report = self.env.ref('tp1_audit_report.audit_report_action')
        # report.write({'name': self._get_report_base_filename()})

        return report.report_action(self, data=data)

    def _get_report_base_filename(self):

        tz = pytz.timezone(self.env.user.tz) or pytz.utc

        name = f"audit_{self.date.strftime('%d%m%Y')}"

        return f"{name}_{pytz.utc.localize(datetime.datetime.now()).astimezone(tz).strftime('%d%m%Y_%H%M%S')}"

