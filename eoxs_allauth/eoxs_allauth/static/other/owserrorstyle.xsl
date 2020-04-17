<?xml version="1.0" encoding="UTF-8"?>

<xsl:stylesheet version="1.0"
xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:ows="http://www.opengis.net/ows/1.1">

<xsl:template match="/">
  <HTML lang="en">

  <HEAD>
    <title>VirES for Swarm</title>
    <link rel="stylesheet" type="text/css" href="/swarm_static/workspace/styles/main.css" />
    <script type="text/javascript" src="/swarm_static/workspace/bower_components/jquery/jquery.min.js"/>
    <script type="text/javascript" src="/swarm_static/workspace/bower_components/bootstrap/dist/js/bootstrap.min.js"/>
    <link href="/swarm_static/css/form_styles.css" rel="stylesheet" />
    <link href="/swarm_static/css/social_providers.css" rel="stylesheet"/>
    <style type="text/css">
        body {
          background-color: #fff!important;
          margin: 0;
          padding: 0;
        }
      </style>
  </HEAD>

  <BODY>
    <div class="navbar navbar-inverse navbar-fixed-top not-selectable" style="position:relative; margin-bottom: 0px">
      <div class="container">
        <div class="navbar-header">
          <button type="button" class="navbar-toggle collapsed" data-toggle="collapse" data-target=".navbar-collapse">
          <span class="icon-bar"></span>
          <span class="icon-bar"></span>
          <span class="icon-bar"></span>
        </button>
            <a class="navbar-brand" href="/" style="font-size:30px">VirES for Swarm</a>
        </div>
        <div class="navbar-collapse collapse">
        </div>
      </div>
    </div>

    <div style="position: relative; height: 95%; height: calc(100% - 50px); overflow-y: scroll; overflow-x: hidden; padding-top: 40px;">
      <div class="row">
        <div class="col-md-4 col-md-offset-4" id="formcontainer">
          <h3><xsl:value-of select="ows:ExceptionReport/ows:Exception/ows:ExceptionText"/></h3>
          <p>Close this tab to return to the application.</p>
        </div>
      </div>
    </div>

  </BODY>
</HTML>

</xsl:template>

</xsl:stylesheet>
