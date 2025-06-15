from flask import Blueprint, redirect, url_for, render_template, flash, request, session, jsonify, current_app
from ..db import get_db_connection, get_cursor
from ..decorators import login_required, admin_required
from datetime import datetime, timedelta
import logging

# Configurar logging
logger = logging.getLogger(__name__)

bp = Blueprint('main', __name__)

# Ruta principal - Redirige al dashboard
@bp.route('/')
@login_required
def index():
    return redirect(url_for('dashboard.home'))

# Clase para manejar la paginación
class Pagination:
    def __init__(self, items, page, per_page, total):
        self.items = items
        self.page = page
        self.per_page = per_page
        self.total = total
        self.pages = (total + per_page - 1) // per_page if total > 0 else 1
        self.has_prev = page > 1
        self.has_next = page < self.pages
        self.prev_num = page - 1 if page > 1 else None
        self.next_num = page + 1 if page < self.pages else None

    def iter_pages(self, left_edge=2, left_current=3, right_current=4, right_edge=2):
        last = 0
        for num in range(1, self.pages + 1):
            if (num <= left_edge or 
                (self.page - left_current - 1 < num < self.page + right_current) or 
                num > self.pages - right_edge):
                if last + 1 != num:
                    yield None
                yield num
                last = num
