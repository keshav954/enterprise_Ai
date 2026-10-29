# Product Restocking & Inventory Policy

## Overview
This document defines the official Enterprise AI Corp standard operating procedure for monitoring stock levels, identifying depleted inventory, and generating purchase requisitions.

## Reorder Policy Guidelines
1. **Critical Reorder Trigger:**
   Whenever an active SKU's current `Stock_Level` falls strictly below its `Reorder_Threshold`, it is classified as **CRITICAL_RESTOCK_REQUIRED**.

2. **Calculation Formula:**
   - `Deficit = Reorder_Threshold - Stock_Level`
   - `Recommended_Order_Quantity = Max(Deficit * 2, 20 units)`

3. **Restocking Priority Order:**
   - High Revenue products (> \$30,000 monthly revenue) with depleted inventory must be prioritized within 24 hours.
   - Hardware products with lead times over 10 business days must receive expedited procurement approval.

4. **Approval Gate:**
   Any restocking order exceeding \$25,000 total procurement value requires managerial sign-off before submission to suppliers.

