<div class="div_workflow">
% _id = workflow['_id']
_id: {{_id}}<br>
name: <span class="editable" id="{{_id}}:name">{{workflow['name']}}</span><br>
query_string: <span class="editable" id="{{_id}}:query_string">{{workflow.get('query_string', '')}}</span><br>
time_elapsed: <span class="editable" id="{{_id}}:time_elapsed">{{int(workflow.get('time_elapsed', 0))}}</span><br>
<%
actions = workflow.get('actions')
if actions is not None:
%>
actions:<br>
<%
    for actioni in range(len(actions)):
%>
<span class="indent1">name: </span><span class="editable" id="{{_id}}:actions.{{actioni}}.name">{{actions[actioni]['name']}}</span><br>
<%
        args = actions[actioni].get('args')
        if args is not None:
%>
<span class="indent1">args:</span><br>
<ul class="indent1">
<%
            for argi in range(len(args)):
%>
<li><span class="editable" id="{{_id}}:actions.{{actioni}}.args.{{argi}}">{{args[argi]}}</span></li>
<%
            end
%>
</ul>
<%
       end
   end
end
prereqs = workflow.get('prereqs')
if prereqs is not None:
%>
prereqs:<br>
<%
    for prereqi in range(len(prereqs)):
%>
<span class="indent1">name: </span><span class="editable" id="{{_id}}:prereqs.{{prereqi}}.name">{{prereqs[prereqi]['name']}}</span><br>
<span class="indent1">time_elapsed: </span><span class="editable" id="{{_id}}:prereqs.{{prereqi}}.time_elapsed">{{int(prereqs[prereqi].get('time_elapsed', 0))}}</span><br>
<%
    end
end
%>
</div>
