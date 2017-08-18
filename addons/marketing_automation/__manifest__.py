# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Marketing Automation',
    'version': '1.0',
    'summary': 'Automate mails',
    'depends': [
        'mass_mailing'  # For design mail templates
    ],
    'data': [
        'security/marketing_automation_security.xml',
        'security/ir.model.access.csv',
        'views/marketing_automation_views.xml',
        'views/marketing_automation_templates.xml',
        'views/inherited_mass_mailing.xml',
        'data/marketing_automation_data.xml'
    ],
    'demo': [
        'data/marketing_automation_demo.xml'
    ],
    'application': True,
    'license': 'OEEL-1'
}
