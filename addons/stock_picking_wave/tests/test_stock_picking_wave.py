# -*- coding: utf-8 -*-

# Author: Tejas Shahu
# Date: 08/14/2017

from odoo.tests import common


class TestStockPickingWave(common.TransactionCase):

    def setUp(self):
        super(TestStockPickingWave, self).setUp()
        print "Test case constructor called"
        self.ProductObj = self.env['product.product']
        self.StockQuantObj = self.env['stock.quant']
        self.InvObj = self.env['stock.inventory']
        self.PickingObj = self.env['stock.picking']

        # Product Created A, B, C
        self.productA = self.ProductObj.create({'name': 'Product A', 'type': 'product'})
        self.productB = self.ProductObj.create({'name': 'Product B', 'type': 'product'})
        self.productC = self.ProductObj.create({'name': 'Product C', 'type': 'product'})
        print "\n\nThree Product created Successfully\n\n"

    def test_warehouse(self):

        print "Warehouse testcase called"
        # Warehouses
        self.warehouse_1 = self.env['stock.warehouse'].create({
            'name': 'Base Warehouse',
            # 'reception_steps': 'one_step',
            # 'delivery_steps': 'ship_only',
            'code': 'BWH'})

        # Locations
        self.location_1 = self.env['stock.location'].create({
            'name': 'TestLocation1',
            # 'posx': 3,
            'location_id': self.warehouse_1.lot_stock_id.id,
        })

        self.location_2 = self.env['stock.location'].create({
            'name': 'TestLocation2',
            # 'posx': 3,
            'location_id': self.warehouse_1.lot_stock_id.id,
        })

        self.location_3 = self.env['stock.location'].create({
            'name': 'TestLocation3',
            # 'posx': 3,
            'location_id': self.warehouse_1.lot_stock_id.id,
        })

        print "\n\nWarehouse and it's 3 location created\n\n"

    def test_updateinventory(self):

        print "Update Inventory started"

        # stocklocation 1
        self.stock_location1 = self.env.ref('stock.stock_location_stock')

        # make some stock
        self.env['stock.quant']._update_available_quantity(
            self.productA, self.stock_location1, 100)

        self.assertEqual(len(self.env['stock.quant']._gather(
            self.productA, self.stock_location1)), 1.0)

        self.assertEqual(self.env['stock.quant']._get_available_quantity(
            self.productA, self.stock_location1), 100.0)

        # check
        self.assertEqual(self.env['stock.quant']._get_available_quantity(
            self.productA, self.stock_location1), 0.0)

        self.assertEqual(len(self.env['stock.quant']._gather(
            self.productA, self.stock_location1)), 0.0)

        # stocklocation 2
        self.stock_location2 = self.env.ref('stock.stock_location_stock')

        # make some stock
        self.env['stock.quant']._update_available_quantity(
            self.productB, self.stock_location2, 200)

        self.assertEqual(len(self.env['stock.quant']._gather(
            self.productB, self.stock_location2)), 1.0)

        self.assertEqual(self.env['stock.quant']._get_available_quantity(
            self.productB, self.stock_location2), 200.0)

        # check
        self.assertEqual(self.env['stock.quant']._get_available_quantity(
            self.productB, self.stock_location2), 0.0)

        self.assertEqual(len(self.env['stock.quant']._gather(
            self.productB, self.stock_location2)), 0.0)

        # stocklocation 3
        self.stock_location3 = self.env.ref('stock.stock_location_stock')

        # make some stock
        self.env['stock.quant']._update_available_quantity(
            self.productC, self.stock_location3, 300)

        self.assertEqual(len(self.env['stock.quant']._gather(
            self.productC, self.stock_location3)), 1.0)

        self.assertEqual(self.env['stock.quant']._get_available_quantity(
            self.productC, self.stock_location3), 300.0)

        # check
        self.assertEqual(self.env['stock.quant']._get_available_quantity(
            self.productC, self.stock_location3), 0.0)

        self.assertEqual(len(self.env['stock.quant']._gather(
            self.productC, self.stock_location3)), 0.0)

        print "\n\nUpdate Inventory Ended\n\n", self.productA,
        self.stock_location1

    def test_outgoingshipment(self):
        # ======================================================================
        # = Create Outgoing shipment with ...
        #   product A ( 10 Unit ) , product B ( 5 Unit )
        #   product C (  3 unit )
        # ======================================================================

        print "Outgoing shipment started"

        # First outgoing shipment
        picking_out = self.PickingObj.create({
            'partner_id': self.partner_agrolite_id,
            'picking_type_id': self.picking_type_out,
            'location_id': self.stock_location1,
            'location_dest_id': self.customer_location})
        move_cust_a = self.MoveObj.create({
            'name': self.productA.name,
            'product_id': self.productA.id,
            'product_uom_qty': 10,
            'product_uom': self.productA.uom_id.id,
            'picking_id': picking_out.id,
            'location_id': self.stock_location1,
            'location_dest_id': self.customer_location})

        print "\n\nOutgoing Shipment:\n\n", self.stock_location1

        # Second outgoing shipment
        picking_out = self.PickingObj.create({
            'partner_id': self.partner_agrolite_id,
            'picking_type_id': self.picking_type_out,
            'location_id': self.stock_location2,
            'location_dest_id': self.customer_location})
        move_cust_b = self.MoveObj.create({
            'name': self.productB.name,
            'product_id': self.productB.id,
            'product_uom_qty': 5,
            'product_uom': self.productB.uom_id.id,
            'picking_id': picking_out.id,
            'location_id': self.stock_location2,
            'location_dest_id': self.customer_location})

        # Third outgoing shipment
        picking_out = self.PickingObj.create({
            'partner_id': self.partner_agrolite_id,
            'picking_type_id': self.picking_type_out,
            'location_id': self.stock_location3,
            'location_dest_id': self.customer_location})
        move_cust_c = self.MoveObj.create({
            'name': self.productC.name,
            'product_id': self.productC.id,
            'product_uom_qty': 3,
            'product_uom': self.productC.uom_id.id,
            'picking_id': picking_out.id,
            'location_id': self.stock_location3,
            'location_dest_id': self.customer_location})

        # Confirm outgoing shipment.
        picking_out.action_confirm()
        for move in picking_out.move_lines:
            self.assertEqual(move.state, 'confirmed', 'Wrong state of move line.')
        # Product assign to outgoing shipments
        picking_out.action_assign()
        self.assertEqual(move_cust_a.state, 'partially_available', 'Wrong state of move line.')
        self.assertEqual(move_cust_b.state, 'assigned', 'Wrong state of move line.')
        self.assertEqual(move_cust_c.state, 'assigned', 'Wrong state of move line.')
        # Check availability for product A
        aval_a_qty = self.MoveObj.search([('product_id', '=', self.productA.id), ('picking_id', '=', picking_out.id)], limit=1).reserved_availability
        self.assertEqual(aval_a_qty, 4.0, 'Wrong move quantity availability of product A (%s found instead of 4)' % (aval_a_qty))
        # Check availability for product B
        aval_b_qty = self.MoveObj.search([('product_id', '=', self.productB.id), ('picking_id', '=', picking_out.id)], limit=1).reserved_availability
        self.assertEqual(aval_b_qty, 5.0, 'Wrong move quantity availability of product B (%s found instead of 5)' % (aval_b_qty))
        # Check availability for product C
        aval_c_qty = self.MoveObj.search([('product_id', '=', self.productC.id), ('picking_id', '=', picking_out.id)], limit=1).reserved_availability
        self.assertEqual(aval_c_qty, 3.0, 'Wrong move quantity availability of product C (%s found instead of 3)' % (aval_c_qty))

        print "Finally Full code executed"