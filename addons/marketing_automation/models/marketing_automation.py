# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from collections import defaultdict
from datetime import timedelta, datetime, date

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.osv import expression
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.safe_eval import safe_eval

import logging
_logger = logging.getLogger(__name__)


class MarketingAutomationCampaign(models.Model):
    _name = 'marketing.automation.campaign'
    _description = 'Marketing Automation Campaign'
    _inherits = {'utm.campaign': 'utm_campaign_id'}

    def _default_model_id(self):
        return self.env['ir.model'].search([('model', '=', 'res.partner')])

    state = fields.Selection([
        ('draft', 'New'),
        ('running', 'Running'),
        ('stopped', 'Stopped')], copy=False, default='draft')
    model_id = fields.Many2one('ir.model', required=True, string='Model', default=lambda self: self._default_model_id(),
        domain="[('field_id.name', '=', 'message_ids'), ('model', '!=', 'mail.thread')]")
    model_name = fields.Char(related='model_id.model', string='Model Name')
    domain = fields.Char(string='Filter', default=[], help='Apply filter on target model before push them into workflow')
    unique_field_id = fields.Many2one('ir.model.fields', string='Unique Field',
        domain="[('model_id', '=', model_id), ('ttype', 'in', ['char', 'int', 'many2one', 'text', 'selection'])]",
        help="Used for avoiding duplicates based on model field.\ne.g. For model 'Customers', Select email field here, If you don't want to process record which have same email address")
    activity_ids = fields.One2many('marketing.automation.activity', 'campaign_id', string='Activities')
    active = fields.Boolean(default=True)
    last_sync_date = fields.Datetime()
    utm_campaign_id = fields.Many2one('utm.campaign', 'Utm Campaign', required=True, ondelete='cascade')
    total_workitems = fields.Integer(compute='_compute_workitems')
    running_workitems = fields.Integer(compute='_compute_workitems')
    completed_workitems = fields.Integer(compute='_compute_workitems')
    is_workitems_outdated = fields.Boolean(compute='_compute_is_workitems_outdated')

    def _compute_workitems(self):
        """Computes the wortitem counts by state"""
        self.env.cr.execute("""
            SELECT
                campaign_id,
                COUNT(CASE WHEN state = 'running' THEN 1 ELSE null END) AS running,
                COUNT(CASE WHEN state = 'completed' THEN 1 ELSE null END) AS completed
            FROM
                marketing_automation_workitem
            WHERE
                campaign_id IN %s
            GROUP BY
                campaign_id;
        """, (tuple(self.ids), ))
        for result in self.env.cr.dictfetchall():
            self.browse(result['campaign_id']).update({
                'total_workitems': result['running'] + result['completed'],
                'running_workitems': result['running'],
                'completed_workitems': result['completed']
            })

    def _compute_is_workitems_outdated(self):
        """ It computes, if there is a possibility of out of sync workitems"""
        for campaign in self:
            activities_changed = campaign.activity_ids.filtered(lambda a: a.interval_update_date >= campaign.last_sync_date or a.create_date >= campaign.last_sync_date)
            if activities_changed and campaign.last_sync_date and campaign.running_workitems:
                campaign.is_workitems_outdated = True
            else:
                campaign.is_workitems_outdated = False

    @api.constrains('activity_ids', 'state')
    def _check_activities(self):
        """ Running campaign must have at least one activity"""
        if self.state == 'running' and not len(self.activity_ids):
            raise ValidationError(_('You must have at least one activity to start this campaign'))

    def no_sync_outdated(self):
        for campaign in self:
            campaign.last_sync_date = fields.datetime.now()

    def sync_outdated(self):
        """ It will synchronize all running workitems which need to update there schedule dates based on change in related activity
            It is done in 2 part:
                1) Update statistics related to updated activities
                2) Create new statistics is user added new activity in workflow
            Here Update/Create is only applied on those statistics which are in valid timespan
            e.g. if user add an activity with 2 hour delay and workitem is older then 2 hour sync_outdated will not create new statistics for such workitems
        """
        Statistics = self.env['marketing.automation.statistics']
        Workitem = self.env['marketing.automation.workitem']
        for campaign in self:

            # If change has been made in existing activities
            activities_changed = campaign.activity_ids.filtered(lambda a: a.interval_update_date >= campaign.last_sync_date)
            stats_to_change = Statistics.search([('state', '=', 'scheduled'),  ('activity_id', 'in', activities_changed.ids)])  # No need to check whether workitem is completed or not because completed workitems don't have scheduled stats
            if stats_to_change:
                stats_to_change._recompute_schedule_date()

            # If new activities added
            activities_added = campaign.activity_ids.filtered(lambda a: a.create_date >= campaign.last_sync_date)
            for act in activities_added:
                if act.trigger_type == 'begin':
                    min_date = (datetime.now() - timedelta(hours=act.delay_in_hours)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                    for wi in Workitem.search([('state', '!=', 'completed'), ('create_date', '>', min_date), ('create_date', '<', act.create_date)]):
                        Statistics.create({
                            'activity_id': act.id,
                            'workitem_id': wi.id,
                            'schedule_date': datetime.strptime(wi.create_date, DEFAULT_SERVER_DATETIME_FORMAT) + timedelta(hours=act.delay_in_hours)
                        })
                elif act.trigger_type in ['act', 'mail_not_open', 'mail_not_click', 'mail_not_reply']:
                    min_date = (datetime.now() - timedelta(hours=act.delay_in_hours)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                    domain = [('workitem_id.state', '!=', 'completed'), ('state', '=', 'processed'), ('activity_id', '=', act.parent_id.id), ('schedule_date', '>', min_date), ('schedule_date', '<', act.create_date)]
                    for stat in Statistics.search(domain):
                        Statistics.create({
                            'activity_id': act.id,
                            'workitem_id': stat.workitem_id.id,
                            'parent_id': stat.id,
                            'schedule_date': datetime.strptime(stat.schedule_date, DEFAULT_SERVER_DATETIME_FORMAT) + timedelta(hours=act.delay_in_hours)
                        })
                else:
                    min_date = (datetime.now() - timedelta(hours=act.delay_in_hours)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                    date_field = act.trigger_type + '_date'
                    domain = [('workitem_id.state', '!=', 'completed'), ('state', '=', 'processed'), ('activity_id', '=', act.parent_id.id), ('schedule_date', '<', act.create_date), '|', (act.trigger_type, '=', False), '&', (act.trigger_type, '=', True), (date_field, '>', min_date)]
                    for stat in Statistics.search(domain):
                        vals = {
                            'activity_id': act.id,
                            'workitem_id': stat.workitem_id.id,
                            'parent_id': stat.id
                        }
                        if stat[act.trigger_type]:
                            vals['schedule_date'] = datetime.strptime(stat.schedule_date, DEFAULT_SERVER_DATETIME_FORMAT) + timedelta(hours=act.delay_in_hours)
                        Statistics.create(vals)
            campaign.no_sync_outdated()

    def start_campaign(self):
        for campaign in self:
            campaign.state = 'running'

    def stop_campaign(self):
        for campaign in self:
            campaign.state = 'stopped'

    def synchronize_target(self):
        """ Responsible for pushing new records in to activity workflow.
            It is done by generating new workitems for records which follow all these rules
                > Records which are not synchronized yet e.g recently created/updated records.
                > Records which are pass the campaign domain filter.
                > Records which not removed by 'unique_field_id' to filter.
        """
        if not self.ids:
            self = self.search([('state', '=', 'running')])  # If called from cron

        Workitem = self.env['marketing.automation.workitem']
        for campaign in self:
            if campaign.state != 'running':  # for manual sync button
                continue
            if not campaign.activity_ids:
                continue
            if not campaign.last_sync_date or not campaign.running_workitems:
                campaign.last_sync_date = fields.Datetime.now()

            CampaignModel = self.env[campaign.model_name]

            # This will fetch new records appeared after last sync
            existing_workitem = Workitem.search_read([('campaign_id', '=', campaign.id), ('test_mode', '=', False)], ['res_id'])
            exclude_ids = [rec['res_id'] for rec in existing_workitem]
            domain = [('id', 'not in', exclude_ids)]

            # If campaign have unique_field_id we need to check uniqueness based on 'unique_field_id' field
            if campaign.unique_field_id and campaign.unique_field_id.name != 'id':
                # Don't use browse maybe record is deleted
                exsiting_records = CampaignModel.search_read([('id', 'in', exclude_ids)])
                unique_field_vals = list(set([rec[campaign.unique_field_id.name] for rec in exsiting_records]))
                unique_domain = [(campaign.unique_field_id.name, 'not in', unique_field_vals)]
                domain = expression.AND([unique_domain, domain])

            if campaign.domain:
                domain = expression.AND([domain, safe_eval(campaign.domain)])

            primary_activities = campaign.activity_ids.filtered(lambda act: act.trigger_type == 'begin')
            statistic_ids = []
            for act in primary_activities:
                schedule_date = datetime.now() + timedelta(hours=act.delay_in_hours)
                statistic_ids.append((0, 0, {
                    'activity_id': act.id,
                    'schedule_date': schedule_date
                }))
            for record in CampaignModel.search(domain):
                Workitem.create({
                    'campaign_id': campaign.id,
                    'res_id': record.id,
                    'statistic_ids': statistic_ids,
                    'test_mode': False
                })

    def process_workitems(self):
        """This will process workitems based on schedule date"""
        if not self.ids:
            self = self.search([('state', '=', 'running')])  # If called from cron

        WorkitemStatistics = self.env['marketing.automation.statistics']
        for campaign in self:
            if campaign.state != 'running':  # for manual sync button
                continue
            WorkitemStatistics.search([
                ('schedule_date', '<=', fields.Datetime.now()),
                ('state', '=', 'scheduled'),
                ('workitem_id.campaign_id', '=', campaign.id),
                ('workitem_id.state', '=', 'running')
            ]).process_workitems_stats()


class MarketingAutomationActivity(models.Model):
    _name = 'marketing.automation.activity'
    _description = 'Marketing Automation Activity'
    _order = 'delay_in_hours'

    _inherits = {'utm.source': 'utm_source_id'}

    # NOTE: another possible activities are SMS, eject from workflow, send a survey
    @api.model
    def _get_activity_type(self):
        return [('email', 'Email'), ('action', 'Server Action')]

    @api.model
    def _default_graph_data(self):
        """Setting default data for empty graph
            > Problem is there is no graph data when user create new activity from kanban
              becasue this field is not computed so no data for graph
        """
        base = date.today() + timedelta(days=-14)
        date_range = [base + timedelta(days=d) for d in range(0, 15)]
        success = []
        rejected = []
        for i in date_range:
            x = i.strftime('%d %b')
            success.append({'x': x, 'y': 0})
            rejected.append({'x': x, 'y': 0})
        return json.dumps([
                {'values': success, 'key': _('Success'), 'area': True, 'color': '#21B799'},
                {'values': rejected, 'key': _('Rejected'), 'area': True, 'color': '#d9534f'}
            ])

    campaign_id = fields.Many2one('marketing.automation.campaign', string='Campaign', ondelete='cascade')
    interval_number = fields.Integer(string='Send after', required=True, default=1)
    interval_type = fields.Selection([('hours', 'Hours'), ('days', 'Days'), ('weeks', 'Weeks'), ('months', 'Months')], default='hours', required=True)
    delay_in_hours = fields.Integer(compute='_compute_delay_in_hours', store=True)
    interval_update_date = fields.Datetime(compute='_compute_delay_in_hours', store=True)  # This is used to notify is there any change in running campaign
    condition = fields.Char(help='Activity will only performed if record satisfy this condition', default=[])
    model_id = fields.Many2one('ir.model', related='campaign_id.model_id', string='Object')
    model_name = fields.Char(related='campaign_id.model_id.model', string='Model Name')
    activity_type = fields.Selection('_get_activity_type', required=True, default='email')
    mass_mailing_id = fields.Many2one('mail.mass_mailing', string='Email Template')
    server_action_id = fields.Many2one('ir.actions.server', string='Server Action')
    utm_source_id = fields.Many2one('utm.source', 'Source', required=True, ondelete='cascade')

    # Related to parent activity
    parent_id = fields.Many2one('marketing.automation.activity', string='Activity', ondelete='cascade')
    child_ids = fields.One2many('marketing.automation.activity', 'parent_id', string='Child Activities')
    trigger_type = fields.Selection([
        ('begin', 'beginning of campaign'),
        ('act', 'another activity'),
        ('mail_open', 'Mail: opened'),
        ('mail_not_open', 'Mail: not opened'),
        ('mail_reply', 'Mail: replied'),
        ('mail_not_reply', 'Mail: not replied'),
        ('mail_click', 'Mail: clicked'),
        ('mail_not_click', 'Mail: not clicked'),
        ('mail_bounce', 'Mail: bounced')
    ], default='begin', required=True)

    # For statistics
    processed = fields.Integer(compute='_compute_statistics')
    rejected = fields.Integer(compute='_compute_statistics')
    total_sent = fields.Integer(compute='_compute_statistics')
    total_click = fields.Integer(compute='_compute_statistics')
    total_open = fields.Integer(compute='_compute_statistics')
    total_reply = fields.Integer(compute='_compute_statistics')
    total_bounce = fields.Integer(compute='_compute_statistics')
    pie_chart_data = fields.Char(compute='_compute_statistics', default=lambda self: self._default_graph_data())

    @api.depends('interval_number', 'interval_type', 'trigger_type')
    def _compute_delay_in_hours(self):
        multi = {'hours': 1, 'days': 24, 'weeks': 7*24, 'months': 30*24}
        for activity in self:
            activity.delay_in_hours = activity.interval_number * multi[activity.interval_type]
            activity.interval_update_date = fields.Datetime.now()

    def _compute_statistics(self):
        """ Compute statistics of the marketing automation activity """
        if not self.ids:
            return

        act_data = dict([(act.id, {}) for act in self])
        for row in self._get_full_statistics():
            act_data[row.pop('activity_id')].update(row)
        for act_id, graph_data in self._get_graph_statistics().items():
            act_data[act_id]['pie_chart_data'] = json.dumps(graph_data)
        for act in self:
            act.update(act_data[act.id])

    @api.constrains('parent_id')
    def _check_parent_id(self):
        for activity in self:
            if not activity._check_recursion():
                raise ValidationError(_('Error! You can\'t create recursive hierarchy of Activity.'))

    def _get_full_statistics(self):
        self.env.cr.execute("""
            SELECT
                stat.activity_id,
                COUNT(CASE WHEN stat.mail_bounce is false THEN 1 ELSE null END) AS total_sent,
                COUNT(CASE WHEN stat.mail_click is true THEN 1 ELSE null END) AS total_click,
                COUNT(CASE WHEN stat.mail_reply is true THEN 1 ELSE null END) AS total_reply,
                COUNT(CASE WHEN stat.mail_open is true THEN 1 ELSE null END) AS total_open,
                COUNT(CASE WHEN stat.mail_bounce is true THEN 1 ELSE null END) AS total_bounce,
                COUNT(CASE WHEN stat.state = 'processed' THEN 1 ELSE null END) AS processed,
                COUNT(CASE WHEN stat.state = 'rejected' THEN 1 ELSE null END) AS rejected
            FROM
                marketing_automation_statistics AS stat
            JOIN
                marketing_automation_workitem AS wi
                ON (stat.workitem_id = wi.id)
            WHERE
                stat.activity_id IN %s AND wi.test_mode = False
            GROUP BY
                stat.activity_id;
        """, (tuple(self.ids), ))

        return self.env.cr.dictfetchall()

    def _get_graph_statistics(self):
        past_date = (datetime.now() + timedelta(days=-14)).strftime('%Y-%m-%d 00:00:00')
        stat_map = {}
        base = date.today() + timedelta(days=-14)
        date_range = [base + timedelta(days=d) for d in range(0, 15)]

        self.env.cr.execute("""
            SELECT
                act.id AS act_id,
                stat.schedule_date::date AS dt,
                count(*) AS total,
                stat.state
            FROM
                marketing_automation_statistics AS stat
            JOIN
                marketing_automation_workitem AS wi
                ON (stat.workitem_id = wi.id)
            JOIN
                marketing_automation_activity AS act
                ON (act.id = stat.activity_id)
            WHERE act.id IN %s AND stat.schedule_date >= %s AND wi.test_mode = False
            GROUP BY act.id , dt, stat.state
            ORDER BY dt;
        """, (tuple(self.ids), past_date))

        for stat in self.env.cr.dictfetchall():
            stat_map[(stat['act_id'], stat['dt'], stat['state'])] = stat['total']

        graph_data = {}
        for act in self:
            success = []
            rejected = []
            for i in date_range:
                x = i.strftime('%d %b')
                success.append({
                    'x': x,
                    'y': stat_map.get((act.id, i.strftime('%Y-%m-%d'), 'processed'), 0)
                })
                rejected.append({
                    'x': x,
                    'y': stat_map.get((act.id, i.strftime('%Y-%m-%d'), 'rejected'), 0)
                })
            graph_data[act.id] = [
                {'values': success, 'key': _('Success'), 'area': True, 'color': '#21B799'},
                {'values': rejected, 'key': _('Rejected'), 'area': True, 'color': '#d9534f'}
            ]
        return graph_data

    def _perform_activity(self, workitems_stats):
        """ Perform current activity on given workitems_stats.
            This will only performed on those workitems_stats which are pass activity conditions
            :param workitems_stats: recordset of workitems_stats going to process by this activity
        """
        self.ensure_one()

        # Separate workitems based on condition (domain)
        condition = []
        permitted_stat = workitems_stats
        rejected_stats = False
        deleted_stats = False
        if self.condition:
            condition = safe_eval(self.condition)
        if condition:
            allowd_ids = self.env[self.model_name].search(condition).ids
            permitted_stat = workitems_stats.filtered(lambda w: w.workitem_id.res_id in allowd_ids)
            rejected_stats = workitems_stats.filtered(lambda w: w.workitem_id.res_id not in allowd_ids)

        # Filter deleted records
        if permitted_stat:
            existing_ids = self.env[self.model_name].search([('id', 'in', permitted_stat.mapped('workitem_id.res_id'))]).ids
            deleted_stats = permitted_stat.filtered(lambda w: w.workitem_id.res_id not in existing_ids)
            permitted_stat = permitted_stat.filtered(lambda w: w.workitem_id.res_id in existing_ids)

        # Process permitted workitems
        method = '_process_with_%s' % (self.activity_type)
        activity_def = getattr(self, method, None)

        if not activity_def:
            _logger.error('Method %s is not implemented on %s object.' % (method, self._name))
            return
        if permitted_stat:
            activity_def(permitted_stat)

        # Process rejected workitems
        if rejected_stats:
            vals = {
                'state': 'rejected',
                'error_msg': _('Rejected by activity filter')
            }
            rejected_stats.write(vals)

        # Process deleted workitems
        if deleted_stats:
            vals = {
                'state': 'error',
                'error_msg': _('Record is deleted')
            }
            deleted_stats.write(vals)

    def _process_with_action(self, workitem_stats):
        """ Responsible for running server actions.
            :param  workitems_stats: marketing.automation.statistics recordset
        """
        if not self.server_action_id:
            return
        error_ids = []
        for stat in workitem_stats:
            # execute server actions
            ctx = {'active_model': self.model_name, 'active_id': stat.workitem_id.res_id}
            try:
                if not stat.workitem_id.test_mode:
                    self.server_action_id.with_context(**ctx).run()
                stat.write({
                    'state': 'processed',
                    'schedule_date': fields.Datetime.now()
                })
            except Exception as e:
                _logger.warning('Action activity "%s" has Error: %s', self.name, e.message)
                stat.write({
                    'state': 'error',
                    'schedule_date': fields.Datetime.now(),
                    'error_msg': _('Exception in server action')
                })
                error_ids.append(stat.id)

        if error_ids:
            workitem_stats = workitem_stats.filtered(lambda stat: stat.id not in error_ids)
        self._genetate_next_stats(workitem_stats)

    def _process_with_email(self, workitem_stats):
        """ Responsible for sending emails.
            :param  workitems_stats: marketing.automation.statistics recordset
        """
        try:
            self.mass_mailing_id.send_mail_automation(self, workitem_stats)
        except Exception as e:
            _logger.warning('Mail activity "%s" has Error: %s', self.name, e.message)
            workitem_stats.write({
                'state': 'error',
                'error_msg': _('Exception in mail template')
            })
            return

        workitem_stats.write({
            'state': 'processed',
            'schedule_date': fields.Datetime.now()
        })
        self._genetate_next_stats(workitem_stats)

    def _genetate_next_stats(self, workitems_stats):
        """Generate child statistics based and compute it's schedule date
            > schedule_date is not computed for mail_open, mail_click, mail_reply, mail_bounce.
            > It will be calculated after getting mail response

            :param  workitems_stats: marketing.automation.statistics recordset
        """
        if self.child_ids:
            WorkitemStatistics = self.env['marketing.automation.statistics']
            for act in self.child_ids:
                trigger_type = act.trigger_type
                for stat in workitems_stats:
                    vals = {
                        'parent_id': stat.id,
                        'workitem_id': stat.workitem_id.id,
                        'activity_id': act.id
                    }
                    if trigger_type in ['act', 'mail_not_open', 'mail_not_click', 'mail_not_reply']:
                        vals['schedule_date'] = datetime.strptime(stat.schedule_date, DEFAULT_SERVER_DATETIME_FORMAT) + timedelta(hours=act.delay_in_hours)
                    WorkitemStatistics.create(vals)


class MarketingAutomationWorkitem(models.Model):
    _name = 'marketing.automation.workitem'
    _rec_name = 'resource_ref'

    @api.model
    def _target_model(self):
        models = self.env['ir.model'].search([('field_id.name', '=', 'message_ids')])
        return [(model.model, model.name) for model in models]

    @api.model
    def default_get(self, default_fields):
        defaults = super(MarketingAutomationWorkitem, self).default_get(default_fields)
        if defaults.get('campaign_id'):
            model_name = self.env['marketing.automation.campaign'].browse(defaults['campaign_id']).model_name
            resource = self.env[model_name].search([], limit=1)
            if resource:
                defaults['resource_ref'] = '%s,%s' % (model_name, resource.id)
        return defaults

    campaign_id = fields.Many2one('marketing.automation.campaign', string='Campaign', ondelete='cascade')
    model_id = fields.Many2one('ir.model', related='campaign_id.model_id', string='Object')
    model_name = fields.Char(related='campaign_id.model_id.model', store=True)
    statistic_ids = fields.One2many('marketing.automation.statistics', 'workitem_id', string='Actions')
    res_id = fields.Integer()
    state = fields.Selection([('running', 'Running'), ('completed', 'Completed')], default='running')
    test_mode = fields.Boolean(default=True)
    resource_ref = fields.Reference(selection='_target_model', compute='_compute_resource_ref', inverse='_inverse_resource_ref')
    test_email = fields.Char('Send Mails To')

    def _compute_resource_ref(self):
        for wi in self:
            wi.resource_ref = '%s,%s' % (wi.model_name, wi.res_id or 0)

    def _inverse_resource_ref(self):
        for wi in self:
            wi.res_id = wi.resource_ref.id

    @api.model
    def create(self, vals):
        res = super(MarketingAutomationWorkitem, self).create(vals)
        if res.test_mode and not res.statistic_ids:
            primary_activities = res.campaign_id.activity_ids.filtered(lambda act: act.trigger_type == 'begin')
            statistic_ids = []
            for act in primary_activities:
                schedule_date = datetime.now() + timedelta(hours=act.delay_in_hours)
                statistic_ids.append((0, 0, {
                    'activity_id': act.id,
                    'schedule_date': schedule_date
                }))
            res.statistic_ids = statistic_ids
        return res

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        if self._context.get('name_update', True):
            args = self._get_implicit_domain(args)
        return super(MarketingAutomationWorkitem, self).search(args, offset, limit, order, count=count)

    def _get_implicit_domain(self, domain):
        """With this user can search by name in any model"""
        if not domain:
            return domain
        replace_domain = []
        search_domain = []
        for d in domain:
            if d[0] == 'display_name':
                replace_domain.append(d)
                search_domain.append((1, '=', 1))
            else:
                search_domain.append(d)
        if replace_domain:
            records = self.with_context(name_update=False).search(search_domain)
            model_dict = defaultdict(list)
            domain_to_replace = {}
            for rec in records:
                model_dict[rec.model_name].append(rec.res_id)
            for d in replace_domain:
                and_domain = []
                for model_name, rec_ids in model_dict.items():
                    model_obj = self.env[model_name]
                    ns_recs = model_obj.name_search(name=d[2], args=[('id', 'in', rec_ids)], operator=d[1], limit=None)
                    and_domain.append(['&', ('model_name', '=', model_name), ('res_id', 'in', [r[0] for r in ns_recs])])
                domain_to_replace[tuple(d)] = expression.OR(and_domain)
            implicit_domain = []
            for d in domain:
                if d[0] == 'display_name':
                    implicit_domain.extend(domain_to_replace[tuple(d)])
                else:
                    implicit_domain.append(d)
            return implicit_domain
        return domain

    def mark_as_completed(self):
        """Manually mark as a completed. It will cancel all child scheduled stat"""
        for wi in self:
            wi.state = 'completed'
            wi.statistic_ids.filtered(lambda stat: stat.state == 'scheduled').write({
                'state': 'cancelled',
                'schedule_date': fields.Datetime.now(),
                'error_msg': _('Marked as completed')
            })


class MarketingAutomationStatistics(models.Model):
    _name = 'marketing.automation.statistics'

    state = fields.Selection([
        ('scheduled', 'Scheduled'),
        ('processed', 'Processed'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
        ('error', 'Error')], default='scheduled')
    activity_id = fields.Many2one('marketing.automation.activity', string='Activity', ondelete='cascade')
    activity_type = fields.Selection(related='activity_id.activity_type')
    workitem_id = fields.Many2one('marketing.automation.workitem', string='Workitem', ondelete='cascade')
    error_msg = fields.Char()
    schedule_date = fields.Datetime()
    parent_id = fields.Many2one('marketing.automation.statistics', string='Parent Activity Statistics', ondelete='cascade')
    trigger_type = fields.Selection(related='activity_id.trigger_type')

    # mail statistics
    mail_click = fields.Boolean()
    mail_click_date = fields.Datetime()
    mail_reply = fields.Boolean()
    mail_reply_date = fields.Datetime()
    mail_open = fields.Boolean()
    mail_open_date = fields.Datetime()
    mail_bounce = fields.Boolean()
    mail_bounce_date = fields.Datetime()

    def process_workitems_stats(self):
        """This will generate workitem batches per activity and process activities with workitems"""
        if not self.ids:
            return
        workitem_batch = defaultdict(lambda: self.env['marketing.automation.statistics'])
        for workitem_stat in self:
            activity = workitem_stat.activity_id
            workitem_batch[activity.id] += workitem_stat

        all_acts = self[0].workitem_id.campaign_id.activity_ids  # All workitem is from same activity so used self[0].campaign_id

        for act in all_acts:
            workitems_stats = workitem_batch.get(act.id, False)
            if workitems_stats:
                act._perform_activity(workitems_stats)
        self._check_completed()

    def cancel_workitems_stats(self):
        for workitem_stat in self:
            workitem_stat.write({'state': 'cancelled', 'schedule_date': fields.Datetime.now()})
        self._check_completed()

    # NOTE: Try to do it with thread so actual redirect or link tracker image get response without send_mail delay (if it getting slow)
    def process_mail_response(self, action):
        """Process action response from mail which are sent via mass_mailing. Its main work is
               > calculate schedule_date for reply, open, click action
               > cancel valid negative stats e.g. if receive mail_click all mail_not_click sibling are going to canceled
               > if mail is bounced all children except mail_bounce are going to canceled

            :param string action: possible values are mail_reply, mail_open, mail_bounce, mail_click
        """
        self.ensure_one()
        if self.workitem_id.campaign_id.state not in ['draft', 'running']:
            return
        # act_to_cancel for cancelled activity which are never going to perform
        # e.g. Once mail is opened mail_not_open actions are useless
        error_msgs = {
            'mail_not_reply': _('This activity is cancelled because parent mail has reply'),
            'mail_not_click': _('This activity is cancelled because parent mail is clicked'),
            'mail_not_open': _('This activity is cancelled because parent mail is opened'),
            'mail_bounce': _('This activity is cancelled because parent mail is bounced')
        }

        child_stats = self.workitem_id.statistic_ids.filtered(lambda stat: stat.parent_id == self and stat.state == 'scheduled')
        if action in ['mail_reply', 'mail_click', 'mail_open'] and not self[action]:
            self.write({action: True, action+'_date': fields.Datetime.now()})
            for stat in child_stats.filtered(lambda stat: stat.activity_id.trigger_type == action):
                if stat.activity_id.delay_in_hours == 0:
                    stat.process_workitems_stats()
                else:
                    stat.write({
                        'schedule_date': datetime.now() + timedelta(hours=stat.activity_id.delay_in_hours)
                    })
            opposite_trigger = action.replace('_', '_not_')
            child_stats.filtered(lambda stat: stat.activity_id.trigger_type == opposite_trigger).write({
                'schedule_date': fields.Datetime.now(),
                'error_msg': error_msgs[opposite_trigger],
                'state': 'cancelled'
            })
            # Some time we got reply and click but mail is still not opened (because tracker img is blocked user mail client)
            if action != 'mail_open' and not self.mail_open:
                self.write({'mail_open': True, 'mail_open_date': fields.Datetime.now()})
                for stat in child_stats.filtered(lambda stat: stat.activity_id.trigger_type == 'mail_open'):
                    if stat.activity_id.delay_in_hours == 0:
                        stat.process_workitems_stats()
                    else:
                        stat.write({
                            'schedule_date': datetime.now() + timedelta(hours=stat.activity_id.delay_in_hours)
                        })
                child_stats.filtered(lambda stat: stat.activity_id.trigger_type == 'mail_not_open').write({
                    'schedule_date': fields.Datetime.now(),
                    'error_msg': error_msgs['mail_not_open'],
                    'state': 'cancelled'
                })
        elif action == 'mail_bounce':
            self.write({'mail_bounce': True, 'mail_bounce_date': fields.Datetime.now()})
            child_stats.filtered(lambda stat: stat.activity_id.trigger_type != 'mail_bounce').write({
                'schedule_date': fields.Datetime.now(),
                'error_msg': error_msgs['mail_bounce'],
                'state': 'cancelled'
            })

    def _recompute_schedule_date(self):
        """Recompute schedule dates. Called from sync_outdated"""
        for stat in self:
            trigger_type = stat.activity_id.trigger_type
            if trigger_type == 'begin':
                stat.schedule_date = datetime.strptime(stat.workitem_id.create_date, DEFAULT_SERVER_DATETIME_FORMAT) + timedelta(hours=stat.activity_id.delay_in_hours)
            elif trigger_type in ['act', 'mail_not_open', 'mail_not_click', 'mail_not_reply']and stat.parent_id:
                stat.schedule_date = datetime.strptime(stat.parent_id.schedule_date, DEFAULT_SERVER_DATETIME_FORMAT) + timedelta(hours=stat.activity_id.delay_in_hours)
            elif stat.parent_id:
                if stat.parent_id[trigger_type]:
                    stat.schedule_date = datetime.strptime(stat.parent_id[trigger_type+'_date'], DEFAULT_SERVER_DATETIME_FORMAT) + timedelta(hours=stat.activity_id.delay_in_hours)
                else:
                    stat.schedule_date = False

    def _check_completed(self):
        """Mark woritem as a complete. It can't be done in batch because user action trigger type don't have fixed time"""
        for workitem_stat in self:
            if not workitem_stat.workitem_id.statistic_ids.filtered(lambda stat: stat.state == 'scheduled'):
                workitem_stat.workitem_id.write({'state': 'completed'})
