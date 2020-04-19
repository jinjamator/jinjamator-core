import logging

from flask import request
from flask_restx import Resource
from jinjamator.daemon.api.serializers import tasks
from jinjamator.daemon.api.parsers import task_arguments
from jinjamator.daemon.api.endpoints.environments import preload_defaults_from_site_choices, site_path_by_name
from jinjamator.daemon.api.restx import api
from jinjamator.tools.docutils_helper import get_section_from_task_doc
from jinjamator.task import JinjamatorTask
from flask import current_app as app
from flask import jsonify
import glob
import os
import xxhash
import json

log = logging.getLogger()

ns = api.namespace('tasks', description='Operations related to jinjamator tasks')

available_tasks_by_id={}
available_tasks_by_path={}
task_models = {}

def discover_tasks(app):

    task_arguments.add_argument('preload-defaults-from-site', type=str, required=False, default='', choices=preload_defaults_from_site_choices, help='Select site within environment to load defaults from, argument format is <environment_name>/<site_name>')

    for tasks_base_dir in app.config["JINJAMATOR_TASKS_BASE_DIRECTORIES"]:            
        for file_ext in ['py','j2']:
            for tasklet_dir in glob.glob( os.path.join(tasks_base_dir,'**',f'*.{file_ext}'), recursive=True):
                task_dir = os.path.dirname(tasklet_dir)
                append = True
                for dir_chunk in task_dir.replace(tasks_base_dir,'').split(os.path.sep): # filter out hidden directories
                    if dir_chunk.startswith(".") or dir_chunk in ['__pycache__']:
                        append = False
                        break
                
                
                if append:
                    dir_name = task_dir.replace(tasks_base_dir,'')[1:]
                    task_id = xxhash.xxh64(task_dir).hexdigest()
                    task_info = {
                            'id':task_id,
                            'path': dir_name,
                            'base_dir': tasks_base_dir,
                            'description': get_section_from_task_doc(task_dir) or 'no description'
                        
                    }
                    if task_id not in available_tasks_by_path:
                        available_tasks_by_path[dir_name]=task_info
                        try:
                            task = JinjamatorTask()
                            log.debug(app.config["JINJAMATOR_FULL_CONFIGURATION"])
                            task._configuration.merge_dict(app.config["JINJAMATOR_FULL_CONFIGURATION"])
                            task.load(os.path.join(task_info['base_dir'],task_info['path']))
                            with app.app_context():
                                data=json.loads(jsonify(task.get_jsonform_schema()['schema']).data.decode('utf-8'))
                            task_models[task_info['path']] = api.schema_model(task_id,data)
                            del task
                            log.info(f'registred model for task {task_dir}')
                            @ns.route(f"/{task_info['path']}", endpoint=task_info['path'])
                            class APIJinjamatorTask(Resource):
                                @api.doc(f"get_task_{task_info['path'].replace(os.path.sep,'_')}_schema")
                                @api.expect(task_arguments)
                                def get(self):
                                    """
                                    Returns the json-schema or the whole alpacajs configuration data for the task
                                    """
                                    args = task_arguments.parse_args(request)
                                    schema_type = args.get('schema-type', 'full')
                                    environment_site = args.get('preload-defaults-from-site')
                                    relative_task_path=request.endpoint.replace('api.','')
                                    task = JinjamatorTask()
                                    task._configuration.merge_dict(app.config["JINJAMATOR_FULL_CONFIGURATION"])
                                    

                                    if environment_site:
                                        task.configuration.merge_yaml(
                                            "{}/defaults.yaml".format(site_path_by_name.get(environment_site))
                                        )
                                    task.load(relative_task_path)
                                    full_schema = task.get_jsonform_schema()
                                    
                                    if schema_type in ['','full']:
                                        response = jsonify(full_schema)
                                    elif schema_type in ['schema']:
                                        response = jsonify(full_schema.get('schema',{}))
                                    elif schema_type in ['data']:
                                        response = jsonify(full_schema.get('data',{}))
                                    elif schema_type in ['options']:
                                        response = jsonify(full_schema.get('options',{}))
                                    elif schema_type in ['view']:
                                        response = jsonify(full_schema.get('view',{}))
                                    del task
                                    return response

                                @api.doc(f"create_task_instance_for_{task_info['path'].replace(os.path.sep,'_')}")
                                @api.expect(task_models[task_info['path']])
                                def post(self):
                                    """
                                    Creates an instance of the task and returns the job_id
                                    """
                                    log.info()
                                    return {}

                        except Exception as e:
                            log.error(f'unable to register {task_dir}: {e}')


@ns.route('/')
class TaskList(Resource):
    @api.marshal_with(tasks)
    def get(self):
        """
        Returns the list of discoverd tasks found in the directories specified by global_tasks_base_dirs.
        """
        
        response = { 'tasks': [] }
        for k,v in available_tasks_by_path.items():
            response['tasks'].append(v)
        
        return response

