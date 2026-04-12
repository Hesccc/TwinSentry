from flask import Blueprint, send_file, current_app, request, jsonify
from ..models import SystemConfig
import os
import io
import re
from ..services.utils import api_response

docs = Blueprint('docs', __name__)




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