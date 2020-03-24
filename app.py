#/usr/bin/env python3


from flask import Flask
from flask_restful import reqparse, abort, Api, Resource, fields, marshal_with

app = Flask(__name__)
api = Api(app)

ENTRIES = {
    'getdose': {
        'task': 'Get dose',
        'description': u'Calculate dose to crystal from a set of input parameters including total exposure',
    },
    'getexposure': {
        'task': 'Get total exposure',
        'description': 'Calculate total exposure in seconds for a crystal can last for a given dose and a set of parameters',
    },
    'todo3': {'task': 'profit!'},
}

resource_fields = {
    'task':   fields.String,
    'description': fields.String,
    'uri':    fields.Url('todo_ep')
}


def abort_if_todo_doesnt_exist(todo_id):
    if todo_id not in ENTRIES:
        abort(404, message="Todo {} doesn't exist".format(todo_id))

parser = reqparse.RequestParser()
parser.add_argument('task')


class TodoDao(object):
    def __init__(self, todo_id, task):
        self.todo_id = todo_id
        self.task = task

        # This field will not be sent in the response
        self.status = 'active'

# Todo
# shows a single todo item and lets you delete a todo item
class Todo(Resource):
    
    def get(self, todo_id):
        abort_if_todo_doesnt_exist(todo_id)
        print(todo_id,ENTRIES[todo_id])
        return {'task': marshal_with(ENTRIES[todo_id],resource_fields)}

#TodoDao(todo_id=todo_id, task=ENTRIES[todo_id]['task'])
#ENTRIES[todo_id]

    def delete(self, todo_id):
        abort_if_todo_doesnt_exist(todo_id)
        del ENTRIES[todo_id]
        return '', 204

    def put(self, todo_id):
        args = parser.parse_args()
        task = {'task': args['task']}
        ENTRIES[todo_id] = task
        return task, 201


# TodoList
# shows a list of all todos, and lets you POST to add new tasks
class TodoList(Resource):
    def get(self):
        return ENTRIES

    def post(self):
        args = parser.parse_args()
        todo_id = int(max(ENTRIES.keys()).lstrip('todo')) + 1
        todo_id = 'todo%i' % todo_id
        ENTRIES[todo_id] = {'task': args['task']}
        return ENTRIES[todo_id], 201


##
## Actually setup the Api resource routing here
##
api.add_resource(TodoList, '/api/v1.0')
api.add_resource(Todo, '/api/v1.0/<todo_id>', endpoint='todo_ep')


if __name__ == '__main__':
    app.run(host='0.0.0.0',debug=True)
