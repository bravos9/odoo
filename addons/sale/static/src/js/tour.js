odoo.define('crm.tour', function(require) {
"use strict";

var tour = require('web_tour.tour');

tour.register('crm_tour', {
    'skip_enabled': true,
}, [{
    trigger: '.o_app[data-menu-xmlid="base.menu_base_partner"], .oe_menu_toggler[data-menu-xmlid="base.menu_base_partner"]',
    content: 'Organize your sales activities with the <b>Sales app</b>.',
    position: 'bottom',
}, {
    trigger: ".oe_kanban_action_button",
    extra_trigger: '.o_salesteam_kanban',
    content: "Let\'s have a look at the quotations of this sales team.",
    position: "bottom"
}, {
    trigger: ".btn-primary.sale-confirm",
    extra_trigger: '.o_sale_order',
    content: "<p><b>Confirm the order</b> if the customer purchases.</p><p><i>The customer can also confirm the order directly from the email he received.</i></p>",
    position: "bottom"
}, {
    trigger: ".o_back_button",
    extra_trigger: ".o_sale_order [data-id='sale'].btn-primary",
    content: "Use the breadcrumd to <b>go back to preceeding screens</b>.",
    position: "bottom"
}, {
    trigger: 'li[data-menu-xmlid="base.menu_sales"], li[data-menu-xmlid="base.menu_sales"]',
    content: "Use this menu to access quotations, sales orders and customers.",
    position: "bottom"
}]);

});
