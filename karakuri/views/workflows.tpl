<!DOCTYPE html>
<html>
<head>
<title>Karakuri Workflows</title>
<link rel="stylesheet" type="text/css" href="/static/default.css">
<script type="text/javascript" src="/static/jquery-2.1.1.min.js"></script>
</head>
<body>
<h1>Workflows</h1>
% for workflow in workflows:
% include('workflow', workflow=workflow)
<br>
% end
</body>
</html>
<script type="text/javascript">
$('.editable').click(
    function() {
        $(this).focus();
        $(this).attr('contentEditable', true);
    }
).blur(
    function(e) {
        $(this).attr('contentEditable', false);
        var tmp = e.target.id.split(':');
        var data = {_id: tmp[0], field: tmp[1], val: e.target.innerText}
        $.post("/editworkflow", data);
    }
);
</script>
