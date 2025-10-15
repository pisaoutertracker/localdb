from flask import Blueprint, jsonify, request, current_app
import threading
import subprocess
import os
import logging
import re
from datetime import datetime

bp = Blueprint('db_sync', __name__)

# Global lock to prevent concurrent sync operations
sync_lock = threading.Lock()
sync_status = {
    'is_running': False,
    'last_run': None,
    'last_status': None,
    'last_message': None,
    'output': None,
    'modules_added': []
}

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

@bp.route('/db_sync/db_info', methods=['GET'])
def get_db_info():
    """Get the current database name that will be synced to"""
    return jsonify({
        'db_name': current_app.config.get('MONGO_DB_NAME', 'Unknown'),
        'mongo_uri': current_app.config.get('MONGO_URI', '').split('@')[-1] if '@' in current_app.config.get('MONGO_URI', '') else 'Unknown'
    }), 200

@bp.route('/db_sync/status', methods=['GET'])
def get_sync_status():
    """Get the current status of the DB sync operation"""
    return jsonify(sync_status), 200

@bp.route('/db_sync/trigger', methods=['POST'])
def trigger_sync():
    """Trigger a DB sync operation"""
    global sync_status
    
    # Check if a sync is already running
    if sync_lock.locked():
        return jsonify({
            'error': 'Sync operation already in progress',
            'status': sync_status
        }), 409  # 409 Conflict
    
    # Get optional parameters from request
    data = request.get_json() or {}
    by_name = data.get('by_name', False)
    location = data.get('location', 'Pisa')
    
    # Extract Flask app config values BEFORE starting the thread
    # (current_app is not available in background threads)
    mongo_uri = current_app.config['MONGO_URI']
    if '?' in mongo_uri:
        mongo_uri = mongo_uri.split('?')[0]
    if '/' in mongo_uri:
        mongo_uri = mongo_uri.rsplit('/', 1)[0]
    
    mongo_db_name = current_app.config['MONGO_DB_NAME']
    api_url = os.environ.get('API_URL', f'http://localhost:{os.environ.get("FLASK_PORT", "5000")}')
    
    # Start sync in background thread
    thread = threading.Thread(
        target=run_sync_operation,
        args=(by_name, location, mongo_uri, mongo_db_name, api_url),
        daemon=True
    )
    thread.start()
    
    return jsonify({
        'message': 'Sync operation started',
        'status': sync_status
    }), 202  # 202 Accepted

def run_sync_operation(by_name, location, mongo_uri, mongo_db_name, api_url):
    """Run the DB sync operation in a separate thread"""
    global sync_status
    
    with sync_lock:
        sync_status['is_running'] = True
        sync_status['last_status'] = 'running'
        sync_status['last_message'] = f'Sync started at {datetime.now().isoformat()}'
        
        try:
            # Get the path to db_sync.py
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            sync_script = os.path.join(base_dir, 'deploy', 'db_sync.py')
            
            # Prepare environment variables with passed config values
            env = os.environ.copy()
            env['MONGO_URI'] = mongo_uri
            env['MONGO_DB_NAME'] = mongo_db_name
            env['API_URL'] = api_url
            
            # Build command
            cmd = ['python3', sync_script]
            if by_name:
                cmd.append('--by-name')
            if location != 'Pisa':
                cmd.extend(['--location', location])
            
            logging.info(f"Running sync command: {' '.join(cmd)}")
            
            # Run the sync script
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=env,
                timeout=600  # 10 minute timeout
            )
            
            if result.returncode == 0:
                sync_status['last_status'] = 'success'
                sync_status['output'] = result.stdout
                
                # Parse output to extract module information
                modules_added = []
                lines = result.stdout.split('\n')
                for i, line in enumerate(lines):
                    # Look for the line with "Missing modules:" (with or without INFO: prefix)
                    if 'Missing modules:' in line and i + 1 < len(lines):
                        # The next line should contain the list of modules
                        try:
                            next_line = lines[i + 1]
                            # Handle both plain list and INFO: prefixed list
                            if 'INFO:' in next_line:
                                # Extract the part after INFO:root: or similar
                                list_part = next_line.split('INFO:', 1)[-1]
                                if ':' in list_part:
                                    list_part = list_part.split(':', 1)[-1]
                                modules_added = re.findall(r"'([^']+)'", list_part.strip())
                            elif next_line.strip().startswith('['):
                                # Direct list format
                                modules_added = re.findall(r"'([^']+)'", next_line)
                        except Exception as e:
                            logging.warning(f"Failed to parse module list: {e}")
                        break
                
                sync_status['modules_added'] = modules_added
                num_modules = len(modules_added)
                sync_status['last_message'] = f'Sync completed successfully. Added {num_modules} module(s) at {datetime.now().isoformat()}'
                logging.info(f"Sync completed successfully. Added {num_modules} modules. Output: {result.stdout}")
            else:
                sync_status['last_status'] = 'error'
                sync_status['last_message'] = f'Sync failed: {result.stderr}'
                sync_status['output'] = result.stderr
                sync_status['modules_added'] = []
                logging.error(f"Sync failed. Error: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            sync_status['last_status'] = 'error'
            sync_status['last_message'] = 'Sync operation timed out'
            sync_status['output'] = None
            sync_status['modules_added'] = []
            logging.error("Sync operation timed out")
        except Exception as e:
            sync_status['last_status'] = 'error'
            sync_status['last_message'] = f'Sync failed with exception: {str(e)}'
            sync_status['output'] = None
            sync_status['modules_added'] = []
            logging.error(f"Sync failed with exception: {str(e)}")
        finally:
            sync_status['is_running'] = False
            sync_status['last_run'] = datetime.now().isoformat()
