<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE xsl:stylesheet [ 
    <!ENTITY nbsp "&#160;">   <!-- white space in XSL -->
    <!ENTITY copy "&#169;">   <!-- copyright symbol in XSL -->
    ]>
    
<!-- 
	This file was produced, and released as part of Cheshire for Archives v3.x.
	Copyright &copy; 2005-2007 the University of Liverpool
-->

<xsl:stylesheet 
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  version="1.0">

	<xsl:output method="xml"/>
	<xsl:preserve-space elements="*"/>

  <!-- templates for Table of Contents (toc) -->
  <xsl:template name="toc">
  	<script type="text/javascript" src="/javascript/collapsibleLists.js"></script>
  	<script type="text/javascript" src="/javascript/cookies.js"></script>
  	
    <h2>Contents 
    	<span class="printlink">
    		<a href="SCRIPT?operation=toc&amp;recid=RECID">[ printable ]</a>
    	</span>
    </h2>
    <xsl:call-template name="toc-link">
      <xsl:with-param name="node" select="/ead/archdesc"/>
    </xsl:call-template>
    <ul id="someId" class="hierarchy">    
		<xsl:apply-templates select="/ead/archdesc/dsc" mode="toc"/>
    </ul>
    <br/>
    <br/>
  </xsl:template>


	<xsl:template match="dsc" mode="toc">
		<xsl:for-each select="c|c01">
			<xsl:if test="not(./@audience and ./@audience = 'internal')">
				<li><xsl:call-template name="toc-c"/></li>
			</xsl:if>
        </xsl:for-each>
	</xsl:template>


	<xsl:template name="toc-c" match="c|c01|c02|c03|c04|c05|c06|c07|c08|c09|c10|c11|c12">
		<xsl:call-template name="toc-link">
			  <xsl:with-param name="node" select="."/>
		</xsl:call-template>
	    <xsl:if test="c|c01|c02|c03|c04|c05|c06|c07|c08|c09|c10|c11|c12">      
	      <ul class="hierarchy">
	        <xsl:for-each select="c|c01|c02|c03|c04|c05|c06|c07|c08|c09|c10|c11|c12">
	        	<xsl:if test="not(./@audience and ./@audience = 'internal')">
		          <li>
		            <xsl:call-template name="toc-c"/>
		          </li>
	         </xsl:if>
	        </xsl:for-each>
	      </ul>
		</xsl:if>
	</xsl:template>


  <xsl:template name="toc-link">
    <xsl:param name="node"/>
    <a>
      <xsl:attribute name="href">
        <xsl:text>PAGE#</xsl:text>
        <xsl:choose>
          <xsl:when test="$node/@id">
            <xsl:value-of select="$node/@id"/>
          </xsl:when>
          <xsl:when test="$node/did/@id">
            <xsl:value-of select="$node/did/@id"/>
          </xsl:when>
          <xsl:when test="$node/did/unitid/@id">
            <xsl:value-of select="$node/did/unitid/@id"/>
          </xsl:when>
          <xsl:otherwise>
			<xsl:value-of select="generate-id(.)"/>
          </xsl:otherwise>
        </xsl:choose>
      </xsl:attribute>
      <xsl:attribute name="onclick">
        <xsl:text>setCookie('RECID-tocstate', stateToString('someId'))</xsl:text>
      </xsl:attribute>
      <xsl:if test="$node/did/unitid">
	      <xsl:value-of select="$node/did/unitid"/>
	      <xsl:text> - </xsl:text>
      </xsl:if>
      <xsl:choose>
      	<xsl:when test="$node/did/unittitle">
		      <xsl:value-of select="$node/did/unittitle"/>
	      </xsl:when>
	      <xsl:when test="$node/../eadheader/filedesc/titlestmt/titleproper">
	      	<xsl:value-of select="$node/../eadheader/filedesc/titlestmt/titleproper"/>
	      </xsl:when>
 	      <xsl:otherwise>
 	      	<xsl:text>(untitled)</xsl:text>
	      </xsl:otherwise>
      </xsl:choose>
    </a>
    <!-- 
    <xsl:if test="$node/did/physdesc/extent">
    	<xsl:text>{</xsl:text>
    		<xsl:value-of select="$node/did/physdesc/extent"/>
    	<xsl:text>}</xsl:text>
    </xsl:if>
     -->
  </xsl:template>

</xsl:stylesheet>