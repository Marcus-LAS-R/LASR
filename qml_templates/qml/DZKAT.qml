<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis labelsEnabled="1" simplifyDrawingTol="1" styleCategories="AllStyleCategories" maxScale="0" readOnly="0" simplifyDrawingHints="1" minScale="1e+08" simplifyLocal="1" hasScaleBasedVisibilityFlag="0" simplifyMaxScale="1" version="3.4.3-Madeira" simplifyAlgorithm="0">
  <flags>
    <Identifiable>1</Identifiable>
    <Removable>1</Removable>
    <Searchable>1</Searchable>
  </flags>
  <renderer-v2 forceraster="0" symbollevels="0" enableorderby="0" type="singleSymbol">
    <symbols>
      <symbol clip_to_extent="1" force_rhr="0" alpha="1" name="0" type="fill">
        <layer locked="0" pass="0" class="SimpleFill" enabled="1">
          <prop v="3x:0,0,0,0,0,0" k="border_width_map_unit_scale"/>
          <prop v="114,155,111,0" k="color"/>
          <prop v="bevel" k="joinstyle"/>
          <prop v="0,0" k="offset"/>
          <prop v="3x:0,0,0,0,0,0" k="offset_map_unit_scale"/>
          <prop v="MM" k="offset_unit"/>
          <prop v="227,26,28,255" k="outline_color"/>
          <prop v="solid" k="outline_style"/>
          <prop v="0.5" k="outline_width"/>
          <prop v="MM" k="outline_width_unit"/>
          <prop v="solid" k="style"/>
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
    <rotation/>
    <sizescale/>
  </renderer-v2>
  <labeling type="simple">
    <settings>
      <text-style fontUnderline="0" fieldName="PARCELNR" blendMode="0" fontLetterSpacing="0" namedStyle="Normalny" useSubstitutions="0" multilineHeight="1" fontStrikeout="0" textOpacity="1" fontWordSpacing="0" fontSizeMapUnitScale="3x:0,0,0,0,0,0" fontSize="10" textColor="227,26,28,255" fontFamily="MS Shell Dlg 2" fontItalic="0" fontCapitals="0" isExpression="0" previewBkgrdColor="#ffffff" fontWeight="50" fontSizeUnit="Point">
        <text-buffer bufferJoinStyle="128" bufferNoFill="0" bufferDraw="1" bufferColor="255,255,255,255" bufferSizeMapUnitScale="3x:0,0,0,0,0,0" bufferBlendMode="0" bufferSize="1" bufferOpacity="1" bufferSizeUnits="MM"/>
        <background shapeRadiiX="0" shapeBorderColor="128,128,128,255" shapeType="0" shapeRadiiUnit="MM" shapeDraw="0" shapeSVGFile="" shapeSizeUnit="MM" shapeOffsetY="0" shapeRadiiMapUnitScale="3x:0,0,0,0,0,0" shapeFillColor="255,255,255,255" shapeBorderWidthMapUnitScale="3x:0,0,0,0,0,0" shapeOffsetUnit="MM" shapeRadiiY="0" shapeBorderWidthUnit="MM" shapeBlendMode="0" shapeRotationType="0" shapeSizeX="0" shapeOffsetX="0" shapeBorderWidth="0" shapeOpacity="1" shapeJoinStyle="64" shapeRotation="0" shapeSizeType="0" shapeSizeMapUnitScale="3x:0,0,0,0,0,0" shapeOffsetMapUnitScale="3x:0,0,0,0,0,0" shapeSizeY="0"/>
        <shadow shadowRadiusUnit="MM" shadowRadiusMapUnitScale="3x:0,0,0,0,0,0" shadowOffsetMapUnitScale="3x:0,0,0,0,0,0" shadowRadiusAlphaOnly="0" shadowColor="0,0,0,255" shadowOffsetDist="1" shadowOffsetGlobal="1" shadowRadius="1,5" shadowBlendMode="6" shadowDraw="0" shadowOpacity="0,7" shadowUnder="0" shadowScale="100" shadowOffsetUnit="MM" shadowOffsetAngle="135"/>
        <substitutions/>
      </text-style>
      <text-format multilineAlign="4294967295" leftDirectionSymbol="&lt;" placeDirectionSymbol="0" formatNumbers="0" decimals="3" rightDirectionSymbol=">" plussign="0" addDirectionSymbol="0" autoWrapLength="0" wrapChar="" useMaxLineLengthForAutoWrap="1" reverseDirectionSymbol="0"/>
      <placement preserveRotation="1" dist="0" fitInPolygonOnly="0" yOffset="0" distUnits="MM" offsetType="0" maxCurvedCharAngleOut="-25" repeatDistanceUnits="MM" placementFlags="10" repeatDistance="0" centroidInside="1" repeatDistanceMapUnitScale="3x:0,0,0,0,0,0" placement="0" rotationAngle="0" distMapUnitScale="3x:0,0,0,0,0,0" labelOffsetMapUnitScale="3x:0,0,0,0,0,0" predefinedPositionOrder="TR,TL,BR,BL,R,L,TSR,BSR" priority="5" offsetUnits="MM" centroidWhole="0" quadOffset="4" maxCurvedCharAngleIn="25" xOffset="0"/>
      <rendering scaleMin="0" minFeatureSize="0" displayAll="1" obstacleType="0" scaleMax="0" fontMinPixelSize="3" scaleVisibility="0" fontMaxPixelSize="10000" upsidedownLabels="0" labelPerPart="0" obstacleFactor="1" fontLimitPixelSize="0" limitNumLabels="0" obstacle="1" maxNumLabels="2000" zIndex="0" mergeLines="0" drawLabels="1"/>
      <dd_properties>
        <Option type="Map">
          <Option value="" name="name" type="QString"/>
          <Option name="properties"/>
          <Option value="collection" name="type" type="QString"/>
        </Option>
      </dd_properties>
    </settings>
  </labeling>
  <customproperties>
    <property key="dualview/previewExpressions">
      <value>"PARCELID"</value>
    </property>
    <property value="0" key="embeddedWidgets/count"/>
    <property key="variableNames"/>
    <property key="variableValues"/>
  </customproperties>
  <blendMode>0</blendMode>
  <featureBlendMode>0</featureBlendMode>
  <layerOpacity>1</layerOpacity>
  <SingleCategoryDiagramRenderer diagramType="Histogram" attributeLegend="1">
    <DiagramCategory opacity="1" minimumSize="0" scaleDependency="Area" labelPlacementMethod="XHeight" barWidth="5" maxScaleDenominator="1e+08" lineSizeType="MM" penWidth="0" backgroundAlpha="255" sizeScale="3x:0,0,0,0,0,0" minScaleDenominator="0" enabled="0" lineSizeScale="3x:0,0,0,0,0,0" sizeType="MM" penAlpha="255" width="15" rotationOffset="270" penColor="#000000" scaleBasedVisibility="0" height="15" backgroundColor="#ffffff" diagramOrientation="Up">
      <fontProperties style="" description="MS Shell Dlg 2,8.25,-1,5,50,0,0,0,0,0"/>
    </DiagramCategory>
  </SingleCategoryDiagramRenderer>
  <DiagramLayerSettings linePlacementFlags="18" dist="0" obstacle="0" zIndex="0" priority="0" placement="1" showAll="1">
    <properties>
      <Option type="Map">
        <Option value="" name="name" type="QString"/>
        <Option name="properties"/>
        <Option value="collection" name="type" type="QString"/>
      </Option>
    </properties>
  </DiagramLayerSettings>
  <geometryOptions geometryPrecision="0" removeDuplicateNodes="0">
    <activeChecks/>
    <checkConfiguration/>
  </geometryOptions>
  <fieldConfiguration>
    <field name="COUNTY">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="DISTRICT">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="MUNICIP">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="COMMUNITY">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="PARCELNR">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="PARCELID">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="GRP">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="ARK">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="NIELES">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="UWAGI">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="PARCEL_AR">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="PARCEL_POW">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
  </fieldConfiguration>
  <aliases>
    <alias field="COUNTY" index="0" name=""/>
    <alias field="DISTRICT" index="1" name=""/>
    <alias field="MUNICIP" index="2" name=""/>
    <alias field="COMMUNITY" index="3" name=""/>
    <alias field="PARCELNR" index="4" name=""/>
    <alias field="PARCELID" index="5" name=""/>
    <alias field="GRP" index="6" name=""/>
    <alias field="ARK" index="7" name=""/>
    <alias field="NIELES" index="8" name=""/>
    <alias field="UWAGI" index="9" name=""/>
    <alias field="PARCEL_AR" index="10" name=""/>
    <alias field="PARCEL_POW" index="11" name=""/>
  </aliases>
  <excludeAttributesWMS/>
  <excludeAttributesWFS/>
  <defaults>
    <default field="COUNTY" applyOnUpdate="0" expression=""/>
    <default field="DISTRICT" applyOnUpdate="0" expression=""/>
    <default field="MUNICIP" applyOnUpdate="0" expression=""/>
    <default field="COMMUNITY" applyOnUpdate="0" expression=""/>
    <default field="PARCELNR" applyOnUpdate="0" expression=""/>
    <default field="PARCELID" applyOnUpdate="0" expression=""/>
    <default field="GRP" applyOnUpdate="0" expression=""/>
    <default field="ARK" applyOnUpdate="0" expression=""/>
    <default field="NIELES" applyOnUpdate="0" expression=""/>
    <default field="UWAGI" applyOnUpdate="0" expression=""/>
    <default field="PARCEL_AR" applyOnUpdate="0" expression=""/>
    <default field="PARCEL_POW" applyOnUpdate="0" expression=""/>
  </defaults>
  <constraints>
    <constraint exp_strength="0" field="COUNTY" notnull_strength="0" constraints="0" unique_strength="0"/>
    <constraint exp_strength="0" field="DISTRICT" notnull_strength="0" constraints="0" unique_strength="0"/>
    <constraint exp_strength="0" field="MUNICIP" notnull_strength="0" constraints="0" unique_strength="0"/>
    <constraint exp_strength="0" field="COMMUNITY" notnull_strength="0" constraints="0" unique_strength="0"/>
    <constraint exp_strength="0" field="PARCELNR" notnull_strength="0" constraints="0" unique_strength="0"/>
    <constraint exp_strength="0" field="PARCELID" notnull_strength="0" constraints="0" unique_strength="0"/>
    <constraint exp_strength="0" field="GRP" notnull_strength="0" constraints="0" unique_strength="0"/>
    <constraint exp_strength="0" field="ARK" notnull_strength="0" constraints="0" unique_strength="0"/>
    <constraint exp_strength="0" field="NIELES" notnull_strength="0" constraints="0" unique_strength="0"/>
    <constraint exp_strength="0" field="UWAGI" notnull_strength="0" constraints="0" unique_strength="0"/>
    <constraint exp_strength="0" field="PARCEL_AR" notnull_strength="0" constraints="0" unique_strength="0"/>
    <constraint exp_strength="0" field="PARCEL_POW" notnull_strength="0" constraints="0" unique_strength="0"/>
  </constraints>
  <constraintExpressions>
    <constraint field="COUNTY" desc="" exp=""/>
    <constraint field="DISTRICT" desc="" exp=""/>
    <constraint field="MUNICIP" desc="" exp=""/>
    <constraint field="COMMUNITY" desc="" exp=""/>
    <constraint field="PARCELNR" desc="" exp=""/>
    <constraint field="PARCELID" desc="" exp=""/>
    <constraint field="GRP" desc="" exp=""/>
    <constraint field="ARK" desc="" exp=""/>
    <constraint field="NIELES" desc="" exp=""/>
    <constraint field="UWAGI" desc="" exp=""/>
    <constraint field="PARCEL_AR" desc="" exp=""/>
    <constraint field="PARCEL_POW" desc="" exp=""/>
  </constraintExpressions>
  <expressionfields/>
  <attributeactions>
    <defaultAction value="{00000000-0000-0000-0000-000000000000}" key="Canvas"/>
  </attributeactions>
  <attributetableconfig sortOrder="0" sortExpression="" actionWidgetStyle="dropDown">
    <columns>
      <column hidden="0" name="COUNTY" width="-1" type="field"/>
      <column hidden="0" name="DISTRICT" width="-1" type="field"/>
      <column hidden="0" name="MUNICIP" width="-1" type="field"/>
      <column hidden="0" name="COMMUNITY" width="-1" type="field"/>
      <column hidden="0" name="PARCELNR" width="-1" type="field"/>
      <column hidden="0" name="PARCELID" width="-1" type="field"/>
      <column hidden="0" name="GRP" width="-1" type="field"/>
      <column hidden="0" name="ARK" width="-1" type="field"/>
      <column hidden="0" name="NIELES" width="-1" type="field"/>
      <column hidden="0" name="UWAGI" width="-1" type="field"/>
      <column hidden="0" name="PARCEL_AR" width="-1" type="field"/>
      <column hidden="0" name="PARCEL_POW" width="-1" type="field"/>
      <column hidden="1" width="-1" type="actions"/>
    </columns>
  </attributetableconfig>
  <conditionalstyles>
    <rowstyles/>
    <fieldstyles/>
  </conditionalstyles>
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
    <field name="ARK" editable="1"/>
    <field name="COMMUNITY" editable="1"/>
    <field name="COUNTY" editable="1"/>
    <field name="DISTRICT" editable="1"/>
    <field name="GRP" editable="1"/>
    <field name="MUNICIP" editable="1"/>
    <field name="NIELES" editable="1"/>
    <field name="PARCELID" editable="1"/>
    <field name="PARCELNR" editable="1"/>
    <field name="PARCEL_AR" editable="1"/>
    <field name="PARCEL_POW" editable="1"/>
    <field name="UWAGI" editable="1"/>
  </editable>
  <labelOnTop>
    <field labelOnTop="0" name="ARK"/>
    <field labelOnTop="0" name="COMMUNITY"/>
    <field labelOnTop="0" name="COUNTY"/>
    <field labelOnTop="0" name="DISTRICT"/>
    <field labelOnTop="0" name="GRP"/>
    <field labelOnTop="0" name="MUNICIP"/>
    <field labelOnTop="0" name="NIELES"/>
    <field labelOnTop="0" name="PARCELID"/>
    <field labelOnTop="0" name="PARCELNR"/>
    <field labelOnTop="0" name="PARCEL_AR"/>
    <field labelOnTop="0" name="PARCEL_POW"/>
    <field labelOnTop="0" name="UWAGI"/>
  </labelOnTop>
  <widgets/>
  <previewExpression>PARCELID</previewExpression>
  <mapTip></mapTip>
  <layerGeometryType>2</layerGeometryType>
</qgis>
