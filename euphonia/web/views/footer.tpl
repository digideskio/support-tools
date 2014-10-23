<script src="//code.jquery.com/jquery-2.1.1.min.js"></script>
<script src="//maxcdn.bootstrapcdn.com/bootstrap/3.2.0/js/bootstrap.min.js"></script>
<script src="//cdn.jsdelivr.net/jquery.hotkeys/0.1.0/jquery.hotkeys.js"></script>
<script src="//cdn.jsdelivr.net/handlebarsjs/1.3.0/handlebars.min.js"></script>
<script src="//cdn.jsdelivr.net/typeahead.js/0.10.5/typeahead.bundle.js"></script>
<script src="/js/spin.min.js"></script>
<script src="/js/ladda.min.js"></script>
<script src="/js/ladda.jquery.min.js"></script>
<script src="/js/form2js.js"></script>
<script src="/js/app.js"></script>
<%
if defined('renderpage'):
%>
    <script src="/js/{{renderpage}}.js"></script>
<%
end
%>
<script src="/js/prettify.js"></script>