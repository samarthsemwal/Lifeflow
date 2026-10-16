from flask import Blueprint, render_template
from app.services.inventory_service import get_realtime_inventory_summary

inventory_bp = Blueprint('inventory', __name__)

@inventory_bp.route('/')
@inventory_bp.route('/live')
def live_view():
    summary = get_realtime_inventory_summary()
    return render_template(
        'inventory/live_inventory.html',
        summary=summary,
        inventory=summary['inventory']
    )
