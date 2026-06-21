# AG-Grid Header and Row Display Fixes

## Problem Summary
AG-Grid headers and rows were not displaying correctly when:
1. Multiple grids were present on the same page
2. Grids were placed inside UI dialogs

## Root Causes Identified

### Issue 1: Header Visibility with Multiple Grids
- The original CSS in `modern_design_system.py` used overly aggressive rules
- Used `border: none !important` which removed visual structure
- No explicit `display`, `visibility`, or `opacity` properties for headers
- CSS specificity conflicts when multiple grids competed for the same classes

### Issue 2: Row Visibility in Dialogs
- AG-Grid's internal containers (`.ag-body-container`, `.ag-center-cols-container`, etc.) were not explicitly set to be visible
- Row containers lacked proper flex display and position properties
- Missing layout triggers after dialog initialization
- No `onGridReady` callbacks to trigger layout calculations

## Solutions Implemented

### 1. Updated `modern_design_system.py`

#### CSS Changes for Header Visibility:
- Separated header CSS rules from row/cell rules for better specificity
- Added explicit `display: flex`, `visibility: visible`, `opacity: 1` to headers
- Set `min-height: 40px` for header containers
- Added rules for all header components: `.ag-header-cell-wrapper`, `.ag-header-group-cell-wrapper`, `.ag-header-cell-text`

#### CSS Changes for Row Visibility in Dialogs:
- Made ALL ag-grid body containers explicitly visible:
  - `.ag-body-container` - display: block, visibility: visible
  - `.ag-body-viewport` - display: block with auto overflow
  - `.ag-center-cols-container` - block display with visibility
  - `.ag-center-cols-viewport` - block display with auto overflow
- Row and cell elements now have:
  - `display: flex` for proper layout
  - `visibility: visible` and `opacity: 1` to prevent hiding
  - `position: relative` with explicit left/top positioning
  - `width: 100%` and `height: auto` with `min-height: 30px`
- Root containers styled with flexbox column layout
- Pinned columns made explicitly visible

### 2. Updated `uiaggridtheme.py`

- Added equivalent visibility rules for the custom `.ag-theme-quartz-custom` theme
- Applied same pattern to all critical elements:
  - Header elements with flex display
  - Body containers with block display
  - Row and cell elements with proper layout
  - Root and root-wrapper with flexbox
  - Pinned column containers

### 3. Updated Dialog Grid Implementations

#### Modified Files:
- `customer_receipt_ui_fixed_v2.py`
- `supplier_payment_ui_fixed_v2.py`
- `expenses.py`

#### Changes Applied:
Added `onGridReady` callback to all dialog grids:

```javascript
'onGridReady': "function(params){ 
    params.api.sizeColumnsToFit && params.api.sizeColumnsToFit(); 
    setTimeout(function(){ 
        params.api.sizeColumnsToFit && params.api.sizeColumnsToFit(); 
        params.api.doLayout && params.api.doLayout(); 
    }, 100); 
}"
```

This callback:
1. Immediately sizes columns to fit
2. Schedules a second layout calculation after 100ms (allows dialog to fully render)
3. Triggers `doLayout()` to recalculate all internal positions

### 4. Created `aggrid_utils.py` (Optional Utility)

Helper functions for managing AG-Grid layouts:
- `get_grid_ready_callback()` - Generates standardized onGridReady callbacks
- `trigger_grid_layout()` - Manually triggers layout for stored grids

Can be used in future implementations to standardize dialog grid setup.

## CSS Property Explanations

| Property | Value | Purpose |
|----------|-------|---------|
| `display` | flex/block | Enables proper layout engine |
| `visibility` | visible | Ensures element is not hidden |
| `opacity` | 1 | Prevents semi-transparent hiding |
| `overflow` | auto/visible | Allows content to be seen |
| `min-height` | 30-40px | Reserves space for content |
| `position` | relative | Enables positioning without overlap |
| `width` | 100% / auto | Ensures full width or natural width |
| `align-items` | center | Vertical centering for cells |
| `z-index` | auto | Prevents stacking context issues |

## Testing Recommendations

1. **Test Multiple Grids on Page**: 
   - Create a page with 2+ aggrid components
   - Verify all headers and rows are visible
   - Test scrolling and selection

2. **Test Grids in Dialogs**:
   - Open settlement/selection dialogs
   - Verify headers and rows are visible
   - Test sorting and filtering
   - Test row selection (checkboxes)

3. **Test Grid Features**:
   - Column resizing
   - Row height adjustments
   - Search/filter functionality
   - Cell editing if enabled

4. **Test Responsive Behavior**:
   - Resize window/dialog
   - Verify grids adapt properly
   - Check overflow handling

## Files Modified

1. `modern_design_system.py` - Added comprehensive AG-Grid CSS rules
2. `uiaggridtheme.py` - Added equivalent rules for custom theme
3. `customer_receipt_ui_fixed_v2.py` - Added onGridReady callbacks
4. `supplier_payment_ui_fixed_v2.py` - Added onGridReady callbacks  
5. `expenses.py` - Added onGridReady callback
6. `aggrid_utils.py` - Created (new utility file)

## Future Recommendations

1. Apply the same `onGridReady` callback pattern to all other dialog grids
2. Consider centralizing grid initialization logic using `aggrid_utils.py`
3. Add a global grid layout refresh function for responsive dialogs
4. Monitor for any CSS conflicts from future updates to AG-Grid library
