from flask import Blueprint, send_file, current_app, request, jsonify
from ..models import SystemConfig
import os
import io
import re
from ..services.utils import api_response

skills = Blueprint('skills', __name__)

def _apply_skill_replacements(content: str, filename: str, base_url: str, analysis_key: str, action_key: str) -> str:
    """Apply dynamic placeholders for downloadable/preview skill artifacts."""
    content = content.replace('http://your-twinsentry-server:5000', base_url)
    content = content.replace('http://192.168.0.2:5000', base_url)

    file_key = action_key if 'action' in filename else analysis_key

    # YAML/markdown generic placeholders
    content = content.replace('your-api-key', file_key)
    content = content.replace('your-analysis-agent-key-here', analysis_key)
    content = content.replace('your-action-agent-key-here', action_key)

    # Backward compatibility for older embedded demo key
    content = content.replace('05b3a520e16a86424fd3c9666cd11fad422ff7e98102f1b02090991aa15c8eda', action_key)
    return content


@skills.route('/api/skills/config')
def get_skills_config():
    analysis_cfg = SystemConfig.query.filter_by(config_key='ANALYSIS_AGENT_KEY').first()
    action_cfg = SystemConfig.query.filter_by(config_key='ACTION_AGENT_KEY').first()
    
    analysis_key = analysis_cfg.config_value if analysis_cfg else "YOUR_ANALYSIS_KEY"
    action_key = action_cfg.config_value if action_cfg else "YOUR_DISPOSITION_KEY"
    base_url = request.host_url.rstrip('/')
    
    # Pre-processed previews for the frontend
    previews = {}
    scripts_dir = os.path.join(current_app.root_path, '..', 'skills', 'TwinSentry', 'scripts')
    for filename in ['analysis_agent_skill.py', 'action_agent_skill.py', 'langchain_wrapper.py', 'dify_tool.yaml']:
        path = os.path.join(scripts_dir, filename)
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
                content = _apply_skill_replacements(
                    content=content,
                    filename=filename,
                    base_url=base_url,
                    analysis_key=analysis_key,
                    action_key=action_key,
                )
                previews[filename] = content

    return api_response(data={
        'server_url': base_url,
        'analysis_agent_key': analysis_key,
        'action_agent_key': action_key,
        'previews': previews
    })

@skills.route('/api/skills/download/<skill_name>')
def download_skill_file(skill_name):
    import tarfile
    
    if not skill_name or '..' in skill_name or '/' in skill_name or '\\' in skill_name:
        return jsonify({'error': 'Invalid skill name'}), 400
    
    skills_root = os.path.abspath(os.path.join(current_app.root_path, '..', 'skills', skill_name))
    if not os.path.exists(skills_root):
        return jsonify({'error': 'Skills directory not found'}), 404

    analysis_cfg = SystemConfig.query.filter_by(config_key='ANALYSIS_AGENT_KEY').first()
    action_cfg = SystemConfig.query.filter_by(config_key='ACTION_AGENT_KEY').first()
    
    analysis_key = analysis_cfg.config_value if analysis_cfg else "YOUR_ANALYSIS_KEY"
    action_key = action_cfg.config_value if action_cfg else "YOUR_DISPOSITION_KEY"
    base_url = request.host_url.rstrip('/')

    memory_file = io.BytesIO()
    with tarfile.open(fileobj=memory_file, mode='w:gz') as tf:
        for root, dirs, files in os.walk(skills_root):
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, skills_root).replace('\\', '/')
                archive_path = f"{skill_name}/{rel_path}"
                
                if file.endswith(('.md', '.py', '.yaml')):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    content = _apply_skill_replacements(
                        content=content,
                        filename=file,
                        base_url=base_url,
                        analysis_key=analysis_key,
                        action_key=action_key,
                    )

                    encoded_content = content.encode('utf-8')
                    tarinfo = tarfile.TarInfo(name=archive_path)
                    tarinfo.size = len(encoded_content)
                    tarinfo.mtime = int(os.stat(file_path).st_mtime)
                    tf.addfile(tarinfo, io.BytesIO(encoded_content))
                else:
                    tf.add(file_path, arcname=archive_path)

        # Include an auto-generated .env file in the tarball only for twinsentry-skill
        if skill_name == 'twinsentry-skill':
            import time
            env_content = f"TWINSENTRY_BASE_URL={base_url}\nANALYSIS_AGENT_KEY={analysis_key}\nACTION_AGENT_KEY={action_key}\nREQUEST_TIMEOUT=30\n".encode('utf-8')
            env_tarinfo = tarfile.TarInfo(name=f"{skill_name}/.env")
            env_tarinfo.size = len(env_content)
            env_tarinfo.mtime = int(time.time())
            tf.addfile(env_tarinfo, io.BytesIO(env_content))
    
    memory_file.seek(0)
    return send_file(
        memory_file,
        mimetype='application/gzip',
        as_attachment=True,
        download_name=f'{skill_name}.tar.gz'
    )
