<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis maxScale="0" simplifyLocal="1" version="3.14.1-Pi" simplifyMaxScale="1" readOnly="0" styleCategories="AllStyleCategories" hasScaleBasedVisibilityFlag="0" labelsEnabled="1" simplifyAlgorithm="0" minScale="100000000" simplifyDrawingTol="1" simplifyDrawingHints="0">
  <flags>
    <Identifiable>1</Identifiable>
    <Removable>1</Removable>
    <Searchable>1</Searchable>
  </flags>
  <temporal accumulate="0" fixedDuration="0" startField="" startExpression="" endExpression="" endField="" durationField="" mode="0" durationUnit="min" enabled="0">
    <fixedRange>
      <start></start>
      <end></end>
    </fixedRange>
  </temporal>
  <renderer-v2 symbollevels="0" type="RuleRenderer" enableorderby="0" forceraster="0">
    <rules key="{a5f84241-4f3a-4041-97b1-9a01545f13eb}">
      <rule label="Iglaste" key="{4e60b9ef-380d-41ad-a82d-83079c49d80d}" symbol="0" filter="&quot;typ&quot; =  'Iglaste'  and &quot;zezwol&quot; = 'nie'"/>
      <rule label="Liściaste" key="{51b5c761-5262-44c6-9397-807bb8620964}" symbol="1" filter="&quot;typ&quot; =  'Liściaste'  and &quot;zezwol&quot; = 'nie'"/>
      <rule label="Iglaste - zezwolenie" key="{9af25ebf-888d-416e-aa3f-8bc9e739989b}" symbol="2" filter="&quot;typ&quot; =  'Iglaste'  and &quot;zezwol&quot; = 'tak'"/>
      <rule label="Liściaste - zezwolenie" key="{925c0e7e-dc65-4379-9adb-8dbe5ea39a1f}" symbol="3" filter="&quot;typ&quot; =  'Liściaste'  and &quot;zezwol&quot; = 'tak'"/>
      <rule key="{2017c9a2-1205-4643-9a06-8fcfa6e73bde}" symbol="4" filter="ELSE"/>
    </rules>
    <symbols>
      <symbol name="0" clip_to_extent="1" alpha="1" type="marker" force_rhr="0">
        <layer class="SvgMarker" pass="0" locked="0" enabled="1">
          <prop k="angle" v="0"/>
          <prop k="color" v="220,223,32,255"/>
          <prop k="fixedAspectRatio" v="0"/>
          <prop k="horizontal_anchor_point" v="1"/>
          <prop k="name" v="X:/innych_firm/ZAKONCZONE/_Brzesko_TomekKanclerski/MAPA/shp/d_iglaste_pom.svg"/>
          <prop k="offset" v="0,0"/>
          <prop k="offset_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="offset_unit" v="MM"/>
          <prop k="outline_color" v="35,35,35,255"/>
          <prop k="outline_width" v="0"/>
          <prop k="outline_width_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="outline_width_unit" v="MM"/>
          <prop k="scale_method" v="diameter"/>
          <prop k="size" v="4"/>
          <prop k="size_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="size_unit" v="MM"/>
          <prop k="vertical_anchor_point" v="1"/>
          <data_defined_properties>
            <Option type="Map">
              <Option value="" name="name" type="QString"/>
              <Option name="properties"/>
              <Option value="collection" name="type" type="QString"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
      <symbol name="1" clip_to_extent="1" alpha="1" type="marker" force_rhr="0">
        <layer class="SvgMarker" pass="0" locked="0" enabled="1">
          <prop k="angle" v="0"/>
          <prop k="color" v="65,204,204,255"/>
          <prop k="fixedAspectRatio" v="0"/>
          <prop k="horizontal_anchor_point" v="1"/>
          <prop k="name" v="X:/innych_firm/ZAKONCZONE/_Brzesko_TomekKanclerski/MAPA/shp/d_lisciaste_pom.svg"/>
          <prop k="offset" v="0,0"/>
          <prop k="offset_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="offset_unit" v="MM"/>
          <prop k="outline_color" v="35,35,35,255"/>
          <prop k="outline_width" v="0"/>
          <prop k="outline_width_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="outline_width_unit" v="MM"/>
          <prop k="scale_method" v="diameter"/>
          <prop k="size" v="4"/>
          <prop k="size_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="size_unit" v="MM"/>
          <prop k="vertical_anchor_point" v="1"/>
          <data_defined_properties>
            <Option type="Map">
              <Option value="" name="name" type="QString"/>
              <Option name="properties"/>
              <Option value="collection" name="type" type="QString"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
      <symbol name="2" clip_to_extent="1" alpha="1" type="marker" force_rhr="0">
        <layer class="SvgMarker" pass="0" locked="0" enabled="1">
          <prop k="angle" v="0"/>
          <prop k="color" v="213,180,60,255"/>
          <prop k="fixedAspectRatio" v="0"/>
          <prop k="horizontal_anchor_point" v="1"/>
          <prop k="name" v="X:/innych_firm/ZAKONCZONE/_Brzesko_TomekKanclerski/MAPA/shp/d_iglaste_pom_cz.svg"/>
          <prop k="offset" v="0,0"/>
          <prop k="offset_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="offset_unit" v="MM"/>
          <prop k="outline_color" v="35,35,35,255"/>
          <prop k="outline_width" v="0"/>
          <prop k="outline_width_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="outline_width_unit" v="MM"/>
          <prop k="scale_method" v="diameter"/>
          <prop k="size" v="4"/>
          <prop k="size_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="size_unit" v="MM"/>
          <prop k="vertical_anchor_point" v="1"/>
          <data_defined_properties>
            <Option type="Map">
              <Option value="" name="name" type="QString"/>
              <Option name="properties"/>
              <Option value="collection" name="type" type="QString"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
      <symbol name="3" clip_to_extent="1" alpha="1" type="marker" force_rhr="0">
        <layer class="SvgMarker" pass="0" locked="0" enabled="1">
          <prop k="angle" v="0"/>
          <prop k="color" v="164,113,88,255"/>
          <prop k="fixedAspectRatio" v="0"/>
          <prop k="horizontal_anchor_point" v="1"/>
          <prop k="name" v="X:/innych_firm/ZAKONCZONE/_Brzesko_TomekKanclerski/MAPA/shp/d_lisciaste_pom_cz.svg"/>
          <prop k="offset" v="0,0"/>
          <prop k="offset_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="offset_unit" v="MM"/>
          <prop k="outline_color" v="35,35,35,255"/>
          <prop k="outline_width" v="0"/>
          <prop k="outline_width_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="outline_width_unit" v="MM"/>
          <prop k="scale_method" v="diameter"/>
          <prop k="size" v="4"/>
          <prop k="size_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="size_unit" v="MM"/>
          <prop k="vertical_anchor_point" v="1"/>
          <data_defined_properties>
            <Option type="Map">
              <Option value="" name="name" type="QString"/>
              <Option name="properties"/>
              <Option value="collection" name="type" type="QString"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
      <symbol name="4" clip_to_extent="1" alpha="1" type="marker" force_rhr="0">
        <layer class="SimpleMarker" pass="0" locked="0" enabled="1">
          <prop k="angle" v="0"/>
          <prop k="color" v="115,17,228,255"/>
          <prop k="horizontal_anchor_point" v="1"/>
          <prop k="joinstyle" v="bevel"/>
          <prop k="name" v="circle"/>
          <prop k="offset" v="0,0"/>
          <prop k="offset_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="offset_unit" v="MM"/>
          <prop k="outline_color" v="35,35,35,255"/>
          <prop k="outline_style" v="solid"/>
          <prop k="outline_width" v="0"/>
          <prop k="outline_width_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="outline_width_unit" v="MM"/>
          <prop k="scale_method" v="diameter"/>
          <prop k="size" v="2"/>
          <prop k="size_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="size_unit" v="MM"/>
          <prop k="vertical_anchor_point" v="1"/>
          <data_defined_properties>
            <Option type="Map">
              <Option value="" name="name" type="QString"/>
              <Option name="properties"/>
              <Option value="collection" name="type" type="QString"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
    </symbols>
  </renderer-v2>
  <labeling type="simple">
    <settings calloutType="simple">
      <text-style previewBkgrdColor="255,255,255,255" fontCapitals="0" textColor="0,0,0,255" fontItalic="0" fontLetterSpacing="0" blendMode="0" fontSize="6" fontUnderline="0" fontKerning="1" fontWordSpacing="0" fontSizeUnit="Point" multilineHeight="1" fontFamily="MS Shell Dlg 2" textOrientation="horizontal" fieldName="id" textOpacity="1" fontSizeMapUnitScale="3x:0,0,0,0,0,0" allowHtml="0" useSubstitutions="0" isExpression="0" fontWeight="50" namedStyle="Normalny" fontStrikeout="0">
        <text-buffer bufferSizeMapUnitScale="3x:0,0,0,0,0,0" bufferOpacity="1" bufferJoinStyle="128" bufferSize="0.6" bufferColor="255,255,255,255" bufferNoFill="1" bufferBlendMode="0" bufferDraw="1" bufferSizeUnits="MM"/>
        <text-mask maskSizeUnits="MM" maskEnabled="0" maskJoinStyle="128" maskOpacity="1" maskSize="1.5" maskType="0" maskSizeMapUnitScale="3x:0,0,0,0,0,0" maskedSymbolLayers=""/>
        <background shapeType="0" shapeSizeType="0" shapeBorderWidth="0" shapeRotationType="0" shapeRadiiMapUnitScale="3x:0,0,0,0,0,0" shapeOffsetMapUnitScale="3x:0,0,0,0,0,0" shapeDraw="0" shapeSizeMapUnitScale="3x:0,0,0,0,0,0" shapeBorderWidthUnit="MM" shapeOpacity="1" shapeRadiiY="0" shapeOffsetY="0" shapeSizeX="0" shapeBorderColor="128,128,128,255" shapeRotation="0" shapeOffsetUnit="MM" shapeSizeUnit="MM" shapeOffsetX="0" shapeSVGFile="" shapeSizeY="0" shapeBorderWidthMapUnitScale="3x:0,0,0,0,0,0" shapeBlendMode="0" shapeFillColor="255,255,255,255" shapeRadiiX="0" shapeRadiiUnit="MM" shapeJoinStyle="64">
          <symbol name="markerSymbol" clip_to_extent="1" alpha="1" type="marker" force_rhr="0">
            <layer class="SimpleMarker" pass="0" locked="0" enabled="1">
              <prop k="angle" v="0"/>
              <prop k="color" v="231,113,72,255"/>
              <prop k="horizontal_anchor_point" v="1"/>
              <prop k="joinstyle" v="bevel"/>
              <prop k="name" v="circle"/>
              <prop k="offset" v="0,0"/>
              <prop k="offset_map_unit_scale" v="3x:0,0,0,0,0,0"/>
              <prop k="offset_unit" v="MM"/>
              <prop k="outline_color" v="35,35,35,255"/>
              <prop k="outline_style" v="solid"/>
              <prop k="outline_width" v="0"/>
              <prop k="outline_width_map_unit_scale" v="3x:0,0,0,0,0,0"/>
              <prop k="outline_width_unit" v="MM"/>
              <prop k="scale_method" v="diameter"/>
              <prop k="size" v="2"/>
              <prop k="size_map_unit_scale" v="3x:0,0,0,0,0,0"/>
              <prop k="size_unit" v="MM"/>
              <prop k="vertical_anchor_point" v="1"/>
              <data_defined_properties>
                <Option type="Map">
                  <Option value="" name="name" type="QString"/>
                  <Option name="properties"/>
                  <Option value="collection" name="type" type="QString"/>
                </Option>
              </data_defined_properties>
            </layer>
          </symbol>
        </background>
        <shadow shadowOffsetGlobal="1" shadowOffsetAngle="135" shadowOpacity="0.7" shadowOffsetDist="1" shadowRadiusUnit="MM" shadowOffsetUnit="MM" shadowRadiusAlphaOnly="0" shadowBlendMode="6" shadowDraw="0" shadowRadiusMapUnitScale="3x:0,0,0,0,0,0" shadowUnder="0" shadowRadius="1.5" shadowScale="100" shadowColor="0,0,0,255" shadowOffsetMapUnitScale="3x:0,0,0,0,0,0"/>
        <dd_properties>
          <Option type="Map">
            <Option value="" name="name" type="QString"/>
            <Option name="properties"/>
            <Option value="collection" name="type" type="QString"/>
          </Option>
        </dd_properties>
        <substitutions/>
      </text-style>
      <text-format placeDirectionSymbol="0" multilineAlign="3" addDirectionSymbol="0" formatNumbers="0" useMaxLineLengthForAutoWrap="1" plussign="0" leftDirectionSymbol="&lt;" rightDirectionSymbol=">" reverseDirectionSymbol="0" decimals="3" wrapChar="" autoWrapLength="0"/>
      <placement dist="4" distMapUnitScale="3x:0,0,0,0,0,0" xOffset="0" geometryGeneratorType="PointGeometry" overrunDistanceMapUnitScale="3x:0,0,0,0,0,0" offsetType="0" quadOffset="4" yOffset="0" labelOffsetMapUnitScale="3x:0,0,0,0,0,0" repeatDistanceMapUnitScale="3x:0,0,0,0,0,0" repeatDistanceUnits="MM" fitInPolygonOnly="0" maxCurvedCharAngleIn="25" geometryGeneratorEnabled="0" centroidInside="0" centroidWhole="0" distUnits="MM" overrunDistance="0" overrunDistanceUnit="MM" layerType="PointGeometry" preserveRotation="1" geometryGenerator="" predefinedPositionOrder="TR,TL,BR,BL,R,L,TSR,BSR" placementFlags="10" placement="0" maxCurvedCharAngleOut="-25" offsetUnits="MM" rotationAngle="0" polygonPlacementFlags="2" repeatDistance="0" priority="10"/>
      <rendering limitNumLabels="0" minFeatureSize="0" scaleVisibility="0" fontLimitPixelSize="0" zIndex="0" obstacleType="1" maxNumLabels="2000" mergeLines="0" labelPerPart="0" fontMinPixelSize="3" obstacle="1" upsidedownLabels="0" obstacleFactor="1" scaleMax="0" fontMaxPixelSize="10000" displayAll="1" scaleMin="0" drawLabels="1"/>
      <dd_properties>
        <Option type="Map">
          <Option value="" name="name" type="QString"/>
          <Option name="properties"/>
          <Option value="collection" name="type" type="QString"/>
        </Option>
      </dd_properties>
      <callout type="simple">
        <Option type="Map">
          <Option value="pole_of_inaccessibility" name="anchorPoint" type="QString"/>
          <Option name="ddProperties" type="Map">
            <Option value="" name="name" type="QString"/>
            <Option name="properties"/>
            <Option value="collection" name="type" type="QString"/>
          </Option>
          <Option value="true" name="drawToAllParts" type="bool"/>
          <Option value="1" name="enabled" type="QString"/>
          <Option value="centroid" name="labelAnchorPoint" type="QString"/>
          <Option value="&lt;symbol name=&quot;symbol&quot; clip_to_extent=&quot;1&quot; alpha=&quot;1&quot; type=&quot;line&quot; force_rhr=&quot;0&quot;>&lt;layer class=&quot;SimpleLine&quot; pass=&quot;0&quot; locked=&quot;0&quot; enabled=&quot;1&quot;>&lt;prop k=&quot;capstyle&quot; v=&quot;square&quot;/>&lt;prop k=&quot;customdash&quot; v=&quot;5;2&quot;/>&lt;prop k=&quot;customdash_map_unit_scale&quot; v=&quot;3x:0,0,0,0,0,0&quot;/>&lt;prop k=&quot;customdash_unit&quot; v=&quot;MM&quot;/>&lt;prop k=&quot;draw_inside_polygon&quot; v=&quot;0&quot;/>&lt;prop k=&quot;joinstyle&quot; v=&quot;bevel&quot;/>&lt;prop k=&quot;line_color&quot; v=&quot;60,60,60,255&quot;/>&lt;prop k=&quot;line_style&quot; v=&quot;solid&quot;/>&lt;prop k=&quot;line_width&quot; v=&quot;0.3&quot;/>&lt;prop k=&quot;line_width_unit&quot; v=&quot;MM&quot;/>&lt;prop k=&quot;offset&quot; v=&quot;0&quot;/>&lt;prop k=&quot;offset_map_unit_scale&quot; v=&quot;3x:0,0,0,0,0,0&quot;/>&lt;prop k=&quot;offset_unit&quot; v=&quot;MM&quot;/>&lt;prop k=&quot;ring_filter&quot; v=&quot;0&quot;/>&lt;prop k=&quot;use_custom_dash&quot; v=&quot;0&quot;/>&lt;prop k=&quot;width_map_unit_scale&quot; v=&quot;3x:0,0,0,0,0,0&quot;/>&lt;data_defined_properties>&lt;Option type=&quot;Map&quot;>&lt;Option value=&quot;&quot; name=&quot;name&quot; type=&quot;QString&quot;/>&lt;Option name=&quot;properties&quot;/>&lt;Option value=&quot;collection&quot; name=&quot;type&quot; type=&quot;QString&quot;/>&lt;/Option>&lt;/data_defined_properties>&lt;/layer>&lt;/symbol>" name="lineSymbol" type="QString"/>
          <Option value="2" name="minLength" type="double"/>
          <Option value="3x:0,0,0,0,0,0" name="minLengthMapUnitScale" type="QString"/>
          <Option value="MM" name="minLengthUnit" type="QString"/>
          <Option value="2" name="offsetFromAnchor" type="double"/>
          <Option value="3x:0,0,0,0,0,0" name="offsetFromAnchorMapUnitScale" type="QString"/>
          <Option value="MM" name="offsetFromAnchorUnit" type="QString"/>
          <Option value="2" name="offsetFromLabel" type="double"/>
          <Option value="3x:0,0,0,0,0,0" name="offsetFromLabelMapUnitScale" type="QString"/>
          <Option value="MM" name="offsetFromLabelUnit" type="QString"/>
        </Option>
      </callout>
    </settings>
  </labeling>
  <customproperties>
    <property value="&quot;TERYT&quot;" key="dualview/previewExpressions"/>
    <property value="0" key="embeddedWidgets/count"/>
    <property key="variableNames"/>
    <property key="variableValues"/>
  </customproperties>
  <blendMode>0</blendMode>
  <featureBlendMode>0</featureBlendMode>
  <layerOpacity>1</layerOpacity>
  <SingleCategoryDiagramRenderer diagramType="Histogram" attributeLegend="1">
    <DiagramCategory spacingUnit="MM" scaleDependency="Area" barWidth="5" maxScaleDenominator="1e+08" spacingUnitScale="3x:0,0,0,0,0,0" penAlpha="255" scaleBasedVisibility="0" labelPlacementMethod="XHeight" enabled="0" showAxis="1" sizeScale="3x:0,0,0,0,0,0" opacity="1" sizeType="MM" penColor="#000000" lineSizeScale="3x:0,0,0,0,0,0" backgroundColor="#ffffff" diagramOrientation="Up" minScaleDenominator="0" penWidth="0" direction="0" height="15" minimumSize="0" lineSizeType="MM" rotationOffset="270" spacing="5" width="15" backgroundAlpha="255">
      <fontProperties description="MS Shell Dlg 2,8.25,-1,5,50,0,0,0,0,0" style=""/>
      <attribute field="" color="#000000" label=""/>
      <axisSymbol>
        <symbol name="" clip_to_extent="1" alpha="1" type="line" force_rhr="0">
          <layer class="SimpleLine" pass="0" locked="0" enabled="1">
            <prop k="capstyle" v="square"/>
            <prop k="customdash" v="5;2"/>
            <prop k="customdash_map_unit_scale" v="3x:0,0,0,0,0,0"/>
            <prop k="customdash_unit" v="MM"/>
            <prop k="draw_inside_polygon" v="0"/>
            <prop k="joinstyle" v="bevel"/>
            <prop k="line_color" v="35,35,35,255"/>
            <prop k="line_style" v="solid"/>
            <prop k="line_width" v="0.26"/>
            <prop k="line_width_unit" v="MM"/>
            <prop k="offset" v="0"/>
            <prop k="offset_map_unit_scale" v="3x:0,0,0,0,0,0"/>
            <prop k="offset_unit" v="MM"/>
            <prop k="ring_filter" v="0"/>
            <prop k="use_custom_dash" v="0"/>
            <prop k="width_map_unit_scale" v="3x:0,0,0,0,0,0"/>
            <data_defined_properties>
              <Option type="Map">
                <Option value="" name="name" type="QString"/>
                <Option name="properties"/>
                <Option value="collection" name="type" type="QString"/>
              </Option>
            </data_defined_properties>
          </layer>
        </symbol>
      </axisSymbol>
    </DiagramCategory>
  </SingleCategoryDiagramRenderer>
  <DiagramLayerSettings dist="0" showAll="1" linePlacementFlags="18" zIndex="0" priority="0" placement="0" obstacle="0">
    <properties>
      <Option type="Map">
        <Option value="" name="name" type="QString"/>
        <Option name="properties"/>
        <Option value="collection" name="type" type="QString"/>
      </Option>
    </properties>
  </DiagramLayerSettings>
  <geometryOptions removeDuplicateNodes="0" geometryPrecision="0">
    <activeChecks/>
    <checkConfiguration/>
  </geometryOptions>
  <referencedLayers/>
  <referencingLayers/>
  <fieldConfiguration>
    <field name="id">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="typ">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="zezwol">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
  </fieldConfiguration>
  <aliases>
    <alias field="id" index="0" name=""/>
    <alias field="typ" index="1" name=""/>
    <alias field="zezwol" index="2" name=""/>
  </aliases>
  <excludeAttributesWMS/>
  <excludeAttributesWFS/>
  <defaults>
    <default field="id" expression="" applyOnUpdate="0"/>
    <default field="typ" expression="" applyOnUpdate="0"/>
    <default field="zezwol" expression="" applyOnUpdate="0"/>
  </defaults>
  <constraints>
    <constraint field="id" constraints="0" exp_strength="0" unique_strength="0" notnull_strength="0"/>
    <constraint field="typ" constraints="0" exp_strength="0" unique_strength="0" notnull_strength="0"/>
    <constraint field="zezwol" constraints="0" exp_strength="0" unique_strength="0" notnull_strength="0"/>
  </constraints>
  <constraintExpressions>
    <constraint exp="" field="id" desc=""/>
    <constraint exp="" field="typ" desc=""/>
    <constraint exp="" field="zezwol" desc=""/>
  </constraintExpressions>
  <expressionfields/>
  <attributeactions>
    <defaultAction value="{00000000-0000-0000-0000-000000000000}" key="Canvas"/>
  </attributeactions>
  <attributetableconfig sortExpression="&quot;pow_krzew&quot;" sortOrder="0" actionWidgetStyle="dropDown">
    <columns>
      <column hidden="1" type="actions" width="-1"/>
      <column name="id" hidden="0" type="field" width="-1"/>
      <column name="typ" hidden="0" type="field" width="-1"/>
      <column name="zezwol" hidden="0" type="field" width="-1"/>
    </columns>
  </attributetableconfig>
  <conditionalstyles>
    <rowstyles/>
    <fieldstyles/>
  </conditionalstyles>
  <storedexpressions/>
  <editform tolerant="1"></editform>
  <editforminit/>
  <editforminitcodesource>0</editforminitcodesource>
  <editforminitfilepath></editforminitfilepath>
  <editforminitcode><![CDATA[# -*- coding: utf-8 -*-
"""
QGIS forms can have a Python function that is called when the form is
opened.

Use this function to add extra logic to your forms.

Enter the name of the function in the "Python Init function"
field.
An example follows:
"""
from qgis.PyQt.QtWidgets import QWidget

def my_form_open(dialog, layer, feature):
	geom = feature.geometry()
	control = dialog.findChild(QWidget, "MyLineEdit")
]]></editforminitcode>
  <featformsuppress>0</featformsuppress>
  <editorlayout>generatedlayout</editorlayout>
  <editable>
    <field editable="1" name="ID_MAPA_D"/>
    <field editable="1" name="ID_MAPA_Dr"/>
    <field editable="1" name="ID_MAPA_Dz"/>
    <field editable="1" name="ID_MAPA_Fo"/>
    <field editable="1" name="ID_MAPA_Na"/>
    <field editable="1" name="ID_MAPA_Pl"/>
    <field editable="1" name="ID_MAPA_Po"/>
    <field editable="1" name="ID_MAPA_Uw"/>
    <field editable="1" name="ID_MAPA__1"/>
    <field editable="1" name="ID_MAPA_h"/>
    <field editable="1" name="ID_MAPA_ob"/>
    <field editable="1" name="ID_MAPA_ś"/>
    <field editable="1" name="NR_DRZEW"/>
    <field editable="1" name="Nr"/>
    <field editable="1" name="TERYT"/>
    <field editable="1" name="d130cm"/>
    <field editable="1" name="d_5cm"/>
    <field editable="1" name="gat_lac"/>
    <field editable="1" name="gat_pl"/>
    <field editable="1" name="h"/>
    <field editable="1" name="id"/>
    <field editable="1" name="lp"/>
    <field editable="1" name="obw130cm"/>
    <field editable="1" name="obw5cm"/>
    <field editable="1" name="obw_130"/>
    <field editable="1" name="pow_krzew"/>
    <field editable="1" name="sum_130"/>
    <field editable="1" name="typ"/>
    <field editable="1" name="zezwol"/>
  </editable>
  <labelOnTop>
    <field name="ID_MAPA_D" labelOnTop="0"/>
    <field name="ID_MAPA_Dr" labelOnTop="0"/>
    <field name="ID_MAPA_Dz" labelOnTop="0"/>
    <field name="ID_MAPA_Fo" labelOnTop="0"/>
    <field name="ID_MAPA_Na" labelOnTop="0"/>
    <field name="ID_MAPA_Pl" labelOnTop="0"/>
    <field name="ID_MAPA_Po" labelOnTop="0"/>
    <field name="ID_MAPA_Uw" labelOnTop="0"/>
    <field name="ID_MAPA__1" labelOnTop="0"/>
    <field name="ID_MAPA_h" labelOnTop="0"/>
    <field name="ID_MAPA_ob" labelOnTop="0"/>
    <field name="ID_MAPA_ś" labelOnTop="0"/>
    <field name="NR_DRZEW" labelOnTop="0"/>
    <field name="Nr" labelOnTop="0"/>
    <field name="TERYT" labelOnTop="0"/>
    <field name="d130cm" labelOnTop="0"/>
    <field name="d_5cm" labelOnTop="0"/>
    <field name="gat_lac" labelOnTop="0"/>
    <field name="gat_pl" labelOnTop="0"/>
    <field name="h" labelOnTop="0"/>
    <field name="id" labelOnTop="0"/>
    <field name="lp" labelOnTop="0"/>
    <field name="obw130cm" labelOnTop="0"/>
    <field name="obw5cm" labelOnTop="0"/>
    <field name="obw_130" labelOnTop="0"/>
    <field name="pow_krzew" labelOnTop="0"/>
    <field name="sum_130" labelOnTop="0"/>
    <field name="typ" labelOnTop="0"/>
    <field name="zezwol" labelOnTop="0"/>
  </labelOnTop>
  <dataDefinedFieldProperties/>
  <widgets/>
  <previewExpression>"TERYT"</previewExpression>
  <mapTip></mapTip>
  <layerGeometryType>0</layerGeometryType>
</qgis>
