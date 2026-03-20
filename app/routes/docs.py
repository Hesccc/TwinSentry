from flask import Blueprint, send_file, current_app, request, jsonify
from ..models import SystemConfig
import os
import io
import re
from ..services.utils import api_response

docs = Blueprint('docs', __name__)


def _apply_skill_replacements(content: str, filename: str, base_url: str, analysis_key: str, dis_key: str) -> str:
    """Apply dynamic placeholders for downloadable/preview skill artifacts."""
    content = content.replace('http://your-twinsentry-server:5000', base_url)
    content = content.replace('http://192.168.0.2:5000', base_url)

    file_key = dis_key if 'disposition' in filename else analysis_key

    # YAML/markdown generic placeholders
    content = content.replace('your-api-key', file_key)
    content = content.replace('your-analysis-agent-key-here', analysis_key)
    content = content.replace('your-disposition-agent-key-here', dis_key)

    # Python skill constants
    if filename == 'analysis_agent_skill.py':
        content = re.sub(
            r'^\s*TWINSENTRY_BASE_URL\s*=\s*["\'][^"\']*["\']',
            f'TWINSENTRY_BASE_URL = "{base_url}"',
            content,
            flags=re.MULTILINE,
        )
        content = re.sub(
            r'^\s*ANALYSIS_AGENT_KEY\s*=\s*["\'][^"\']*["\']',
            f'ANALYSIS_AGENT_KEY  = "{analysis_key}"',
            content,
            flags=re.MULTILINE,
        )

    if filename == 'disposition_agent_skill.py':
        content = re.sub(
            r'^\s*TWINSENTRY_BASE_URL\s*=\s*["\'][^"\']*["\']',
            f'TWINSENTRY_BASE_URL   = "{base_url}"',
            content,
            flags=re.MULTILINE,
        )
        content = re.sub(
            r'^\s*DISPOSITION_AGENT_KEY\s*=\s*["\'][^"\']*["\']',
            f'DISPOSITION_AGENT_KEY = "{dis_key}"',
            content,
            flags=re.MULTILINE,
        )

    # Backward compatibility for older embedded demo key
    content = content.replace('05b3a520e16a86424fd3c9666cd11fad422ff7e98102f1b02090991aa15c8eda', dis_key)
    return content

@docs.route('/api-docs')
def api_docs_json():
    return api_response(data={
        'name': 'TwinSentry API',
        'endpoints': {
            'Webhook': '/api/webhook/receiver (POST)',
            'Analysis Fetch': '/analysis/fetch (GET)',
            'Analysis Submit': '/analysis/submit (POST)',
            'Process/Disposition Fetch': '/disposition/fetch (GET)',
            'Process/Disposition Submit': '/disposition/submit (POST)',
            'System Status': '/api/status (GET)',
            'System Health': '/api/health (GET)'
        }
    })

@docs.route('/api/skills/config')
def get_skills_config():
    analysis_cfg = SystemConfig.query.filter_by(config_key='ANALYSIS_AGENT_KEY').first()
    disposition_cfg = SystemConfig.query.filter_by(config_key='DISPOSITION_AGENT_KEY').first()
    
    analysis_key = analysis_cfg.config_value if analysis_cfg else "YOUR_ANALYSIS_KEY"
    dis_key = disposition_cfg.config_value if disposition_cfg else "YOUR_DISPOSITION_KEY"
    base_url = request.host_url.rstrip('/')
    
    # Pre-processed previews for the frontend
    previews = {}
    scripts_dir = os.path.join(current_app.root_path, '..', 'Skills', 'TwinSentry', 'scripts')
    for filename in ['analysis_agent_skill.py', 'disposition_agent_skill.py', 'langchain_wrapper.py', 'dify_tool.yaml']:
        path = os.path.join(scripts_dir, filename)
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
                content = _apply_skill_replacements(
                    content=content,
                    filename=filename,
                    base_url=base_url,
                    analysis_key=analysis_key,
                    dis_key=dis_key,
                )
                previews[filename] = content

    return api_response(data={
        'server_url': base_url,
        'analysis_agent_key': analysis_key,
        'disposition_agent_key': dis_key,
        'previews': previews
    })

@docs.route('/api/skills/download')
def download_skill_file():
    import zipfile
    
    skills_root = os.path.abspath(os.path.join(current_app.root_path, '..', 'Skills', 'TwinSentry'))
    if not os.path.exists(skills_root):
        return jsonify({'error': 'Skills directory not found'}), 404

    analysis_cfg = SystemConfig.query.filter_by(config_key='ANALYSIS_AGENT_KEY').first()
    disposition_cfg = SystemConfig.query.filter_by(config_key='DISPOSITION_AGENT_KEY').first()
    
    analysis_key = analysis_cfg.config_value if analysis_cfg else "YOUR_ANALYSIS_KEY"
    dis_key = disposition_cfg.config_value if disposition_cfg else "YOUR_DISPOSITION_KEY"
    base_url = request.host_url.rstrip('/')

    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(skills_root):
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, skills_root)
                
                if file.endswith(('.md', '.py', '.yaml')):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    content = _apply_skill_replacements(
                        content=content,
                        filename=file,
                        base_url=base_url,
                        analysis_key=analysis_key,
                        dis_key=dis_key,
                    )

                    zf.writestr(rel_path, content)
                else:
                    zf.write(file_path, rel_path)
    
    memory_file.seek(0)
    return send_file(
        memory_file,
        mimetype='application/zip',
        as_attachment=True,
        download_name='TwinSentry_Skills_Package.zip'
    )
