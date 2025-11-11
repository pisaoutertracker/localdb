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
    'modules_added': [],
    'progress': {
        'current': 0,
        'total': 0,
        'step': '',
        'current_module': ''
    }
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
        # Reset sync_status to avoid cached values
        sync_status['is_running'] = True
        sync_status['last_status'] = 'running'
        sync_status['last_message'] = f'Sync started at {datetime.now().isoformat()}'
        sync_status['output'] = ''
        sync_status['modules_added'] = []
        sync_status['progress'] = {
            'current': 0,
            'total': 0,
            'step': '',
            'current_module': '',
            'action': ''
        }
        
        try:
            # Get the path to db_sync.py
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            sync_script = os.path.join(base_dir, 'scripts', 'db_sync.py')
            
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
            
            # Log environment and command details
            logging.info("="*80)
            logging.info("STARTING DB SYNC FROM WEB INTERFACE")
            logging.info("="*80)
            logging.info(f"Command: {' '.join(cmd)}")
            logging.info(f"Environment variables:")
            logging.info(f"  MONGO_URI: {mongo_uri}")
            logging.info(f"  MONGO_DB_NAME: {mongo_db_name}")
            logging.info(f"  API_URL: {api_url}")
            logging.info(f"Script path: {sync_script}")
            logging.info(f"Working directory: {os.getcwd()}")
            logging.info("="*80)
            
            # Add environment info to output
            sync_status['output'] = f"""{'='*80}
                STARTING DB SYNC FROM WEB INTERFACE
                {'='*80}
                Command: {' '.join(cmd)}
                Environment variables:
                MONGO_URI: {mongo_uri}
                MONGO_DB_NAME: {mongo_db_name}
                API_URL: {api_url}
                Script path: {sync_script}
                Working directory: {os.getcwd()}
                {'='*80}

                """
            
            # Run the sync script with real-time output parsing
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
                bufsize=1  # Line buffered
            )
            
            output_lines = []
            # Read output line by line and update progress
            for line in iter(process.stdout.readline, ''):
                if line:
                    output_lines.append(line)
                    sync_status['output'] += line
                    # Parse progress from lines like:
                    # "Progress: 5/10 - Importing NEW module PS_26_IPG-10013"
                    # "Progress: 5/10 - Updating EXISTING module PS_26_IPG-10013"
                    if 'Progress:' in line:
                        try:
                            # Try to match with action (Importing/Updating)
                            match = re.search(r'Progress: (\d+)/(\d+) - (Importing NEW|Updating EXISTING) module (.+)', line)
                            if match:
                                action = "Importing" if "Importing" in match.group(3) else "Updating"
                                sync_status['progress'] = {
                                    'current': int(match.group(1)),
                                    'total': int(match.group(2)),
                                    'current_module': match.group(4).strip(),
                                    'action': action
                                }
                            else:
                                # Fallback to old format
                                match = re.search(r'Progress: (\d+)/(\d+) - Processing (.+)', line)
                                if match:
                                    sync_status['progress'] = {
                                        'current': int(match.group(1)),
                                        'total': int(match.group(2)),
                                        'current_module': match.group(3).strip(),
                                        'action': 'Processing'
                                    }
                        except:
                            pass
                    # Update step information
                    elif 'STEP' in line:
                        try:
                            match = re.search(r'STEP (\d+/\d+): (.+)', line)
                            if match:
                                sync_status['progress']['step'] = f"Step {match.group(1)}: {match.group(2)}"
                        except:
                            pass
            
            process.wait(timeout=600)
            stderr_output = process.stderr.read()
            
            # Combine output
            result_stdout = ''.join(output_lines)
            result = type('obj', (object,), {
                'returncode': process.returncode,
                'stdout': result_stdout,
                'stderr': stderr_output
            })
            
            if result.returncode == 0:
                sync_status['last_status'] = 'success'
                sync_status['output'] = result.stdout
                
                # Parse output to extract module information
                modules_added = []
                num_new = 0
                num_updated = 0
                lines = result.stdout.split('\n')
                
                for i, line in enumerate(lines):
                    # Look for "New modules:" to get the list of added modules
                    if 'New modules:' in line and i + 1 < len(lines):
                        try:
                            next_line = lines[i + 1]
                            if 'INFO:' in next_line:
                                list_part = next_line.split('INFO:', 1)[-1]
                                if ':' in list_part:
                                    list_part = list_part.split(':', 1)[-1]
                                modules_added = re.findall(r"'([^']+)'", list_part.strip())
                            elif next_line.strip().startswith('['):
                                modules_added = re.findall(r"'([^']+)'", next_line)
                        except Exception as e:
                            logging.warning(f"Failed to parse new modules list: {e}")
                    
                    # Look for the final summary line:
                    # "Sync completed successfully. Imported X new module(s), updated Y existing module(s)."
                    if 'Imported' in line and 'updated' in line:
                        try:
                            match = re.search(r'Imported (\d+) new module\(s\), updated (\d+) existing module\(s\)', line)
                            if match:
                                num_new = int(match.group(1))
                                num_updated = int(match.group(2))
                        except Exception as e:
                            logging.warning(f"Failed to parse sync summary: {e}")
                
                sync_status['modules_added'] = modules_added
                
                # Build status message with details about what was done
                if num_new > 0 and num_updated > 0:
                    sync_status['last_message'] = f'✓ {num_new} new module(s) imported, {num_updated} existing module(s) updated (details and children fields)'
                elif num_new > 0:
                    sync_status['last_message'] = f'✓ {num_new} new module(s) imported to local DB'
                elif num_updated > 0:
                    sync_status['last_message'] = f'✓ 0 new modules imported, {num_updated} existing module(s) updated in local DB (details and children fields)'
                else:
                    sync_status['last_message'] = f'✓ Sync completed, no changes needed'
                
                # Store counts for HTML display
                sync_status['num_new'] = num_new
                sync_status['num_updated'] = num_updated
                
                logging.info(f"Sync completed. New: {num_new}, Updated: {num_updated}")
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
