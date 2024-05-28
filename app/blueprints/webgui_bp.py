from flask import Blueprint, render_template

bp = Blueprint('main', __name__)

@bp.route('/')
def homeGUI():
    return render_template('home.html')

@bp.route('/connect_cables.html')
def connectGUI():
    return render_template('connect_cables.html')

@bp.route('/disconnect_cables.html')
def disconnectGUI():
    return render_template('disconnect_cables.html')
