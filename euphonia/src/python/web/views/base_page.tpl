<!DOCTYPE html>

<html lang="en" xmlns:ng="http://angularjs.org" ng-app="euphonia">
  <head>
      <link rel="stylesheet" href="//maxcdn.bootstrapcdn.com/bootstrap/3.2.0/css/bootstrap.min.css"/>
  </head>
  <body>
      % include('header.tpl')
      % if defined('renderpage'):
      %      include(renderpage)
    <script src="//ajax.googleapis.com/ajax/libs/angularjs/1.2.21/angular.min.js"></script>
    <script src="/js/ui-bootstrap-tpls-0.11.0.min.js"></script>
    <script src="/js/summary.js"></script>
  </body>
</html>