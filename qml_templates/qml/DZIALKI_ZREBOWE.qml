<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis simplifyMaxScale="1" hasScaleBasedVisibilityFlag="1" simplifyAlgorithm="0" simplifyDrawingHints="1" simplifyLocal="1" maxScale="0" minScale="10050" styleCategories="AllStyleCategories" readOnly="0" labelsEnabled="1" version="3.14.1-Pi" simplifyDrawingTol="1">
  <flags>
    <Identifiable>1</Identifiable>
    <Removable>1</Removable>
    <Searchable>1</Searchable>
  </flags>
  <temporal startField="" endField="" fixedDuration="0" enabled="0" accumulate="0" endExpression="" durationField="" mode="0" startExpression="" durationUnit="min">
    <fixedRange>
      <start></start>
      <end></end>
    </fixedRange>
  </temporal>
  <renderer-v2 forceraster="0" type="RuleRenderer" enableorderby="0" symbollevels="0">
    <rules key="{ca6f00eb-fc34-433d-93b0-30342a0601fb}">
      <rule label="Rębnia I (początek planu)" symbol="0" key="{551d15fe-e993-4074-8244-0759bbc63f8c}" filter=" &quot;DZ_ZRB&quot; = 'Ipocz'"/>
      <rule label="Rębnia I (koniec planu)" symbol="1" key="{a41317cf-ff56-4010-adb3-0a68faae889c}" filter="&quot;DZ_ZRB&quot; = 'Ikon'"/>
      <rule label="Rębnia I" symbol="2" key="{4269f41d-a320-4e83-94f4-31d3d17acf3f}" filter="&quot;DZ_ZRB&quot; = 'I'"/>
      <rule label="Rębnie złożone" symbol="3" key="{7ef46ea0-83aa-4eea-a3d8-7a2c54d89b49}" filter="&quot;DZ_ZRB&quot; = 'zloz'"/>
      <rule label="Rębnia I (dz. zrębowe osłonowe pozostające do trzebierzy)" symbol="4" key="{987e6b28-b0db-4b46-8d1a-a845db032818}" filter="&quot;DZ_ZRB&quot; = 'Ioslo'"/>
    </rules>
    <symbols>
      <symbol type="fill" name="0" force_rhr="0" clip_to_extent="1" alpha="1">
        <layer enabled="1" class="LinePatternFill" pass="0" locked="0">
          <prop k="angle" v="-45"/>
          <prop k="color" v="125,139,143,255"/>
          <prop k="distance" v="5"/>
          <prop k="distance_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="distance_unit" v="MM"/>
          <prop k="line_width" v="0.26"/>
          <prop k="line_width_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="line_width_unit" v="MM"/>
          <prop k="offset" v="0"/>
          <prop k="offset_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="offset_unit" v="MM"/>
          <prop k="outline_width_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="outline_width_unit" v="MM"/>
          <data_defined_properties>
            <Option type="Map">
              <Option value="" type="QString" name="name"/>
              <Option name="properties"/>
              <Option value="collection" type="QString" name="type"/>
            </Option>
          </data_defined_properties>
          <symbol type="line" name="@0@0" force_rhr="0" clip_to_extent="1" alpha="1">
            <layer enabled="1" class="SimpleLine" pass="0" locked="0">
              <prop k="capstyle" v="square"/>
              <prop k="customdash" v="5;2"/>
              <prop k="customdash_map_unit_scale" v="3x:0,0,0,0,0,0"/>
              <prop k="customdash_unit" v="MM"/>
              <prop k="draw_inside_polygon" v="0"/>
              <prop k="joinstyle" v="bevel"/>
              <prop k="line_color" v="143,0,2,255"/>
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
                  <Option value="" type="QString" name="name"/>
                  <Option name="properties"/>
                  <Option value="collection" type="QString" name="type"/>
                </Option>
              </data_defined_properties>
            </layer>
          </symbol>
        </layer>
        <layer enabled="1" class="SimpleFill" pass="0" locked="0">
          <prop k="border_width_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="color" v="245,0,0,255"/>
          <prop k="joinstyle" v="bevel"/>
          <prop k="offset" v="0,0"/>
          <prop k="offset_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="offset_unit" v="MM"/>
          <prop k="outline_color" v="143,0,2,255"/>
          <prop k="outline_style" v="solid"/>
          <prop k="outline_width" v="0.26"/>
          <prop k="outline_width_unit" v="MM"/>
          <prop k="style" v="no"/>
          <data_defined_properties>
            <Option type="Map">
              <Option value="" type="QString" name="name"/>
              <Option name="properties"/>
              <Option value="collection" type="QString" name="type"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
      <symbol type="fill" name="1" force_rhr="0" clip_to_extent="1" alpha="1">
        <layer enabled="1" class="LinePatternFill" pass="0" locked="0">
          <prop k="angle" v="45"/>
          <prop k="color" v="133,182,111,255"/>
          <prop k="distance" v="5"/>
          <prop k="distance_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="distance_unit" v="MM"/>
          <prop k="line_width" v="0.26"/>
          <prop k="line_width_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="line_width_unit" v="MM"/>
          <prop k="offset" v="0"/>
          <prop k="offset_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="offset_unit" v="MM"/>
          <prop k="outline_width_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="outline_width_unit" v="MM"/>
          <data_defined_properties>
            <Option type="Map">
              <Option value="" type="QString" name="name"/>
              <Option name="properties"/>
              <Option value="collection" type="QString" name="type"/>
            </Option>
          </data_defined_properties>
          <symbol type="line" name="@1@0" force_rhr="0" clip_to_extent="1" alpha="1">
            <layer enabled="1" class="SimpleLine" pass="0" locked="0">
              <prop k="capstyle" v="square"/>
              <prop k="customdash" v="5;2"/>
              <prop k="customdash_map_unit_scale" v="3x:0,0,0,0,0,0"/>
              <prop k="customdash_unit" v="MM"/>
              <prop k="draw_inside_polygon" v="0"/>
              <prop k="joinstyle" v="bevel"/>
              <prop k="line_color" v="182,0,3,255"/>
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
                  <Option value="" type="QString" name="name"/>
                  <Option name="properties"/>
                  <Option value="collection" type="QString" name="type"/>
                </Option>
              </data_defined_properties>
            </layer>
          </symbol>
        </layer>
        <layer enabled="1" class="SimpleFill" pass="0" locked="0">
          <prop k="border_width_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="color" v="143,0,2,255"/>
          <prop k="joinstyle" v="bevel"/>
          <prop k="offset" v="0,0"/>
          <prop k="offset_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="offset_unit" v="MM"/>
          <prop k="outline_color" v="143,0,2,255"/>
          <prop k="outline_style" v="solid"/>
          <prop k="outline_width" v="0.26"/>
          <prop k="outline_width_unit" v="MM"/>
          <prop k="style" v="no"/>
          <data_defined_properties>
            <Option type="Map">
              <Option value="" type="QString" name="name"/>
              <Option name="properties"/>
              <Option value="collection" type="QString" name="type"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
      <symbol type="fill" name="2" force_rhr="0" clip_to_extent="1" alpha="1">
        <layer enabled="1" class="PointPatternFill" pass="0" locked="0">
          <prop k="displacement_x" v="1.2"/>
          <prop k="displacement_x_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="displacement_x_unit" v="MM"/>
          <prop k="displacement_y" v="0"/>
          <prop k="displacement_y_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="displacement_y_unit" v="MM"/>
          <prop k="distance_x" v="2.4"/>
          <prop k="distance_x_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="distance_x_unit" v="MM"/>
          <prop k="distance_y" v="2.4"/>
          <prop k="distance_y_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="distance_y_unit" v="MM"/>
          <prop k="offset_x" v="0"/>
          <prop k="offset_x_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="offset_x_unit" v="MM"/>
          <prop k="offset_y" v="0"/>
          <prop k="offset_y_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="offset_y_unit" v="MM"/>
          <prop k="outline_width_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="outline_width_unit" v="MM"/>
          <data_defined_properties>
            <Option type="Map">
              <Option value="" type="QString" name="name"/>
              <Option name="properties"/>
              <Option value="collection" type="QString" name="type"/>
            </Option>
          </data_defined_properties>
          <symbol type="marker" name="@2@0" force_rhr="0" clip_to_extent="1" alpha="1">
            <layer enabled="1" class="SimpleMarker" pass="0" locked="0">
              <prop k="angle" v="0"/>
              <prop k="color" v="255,0,0,255"/>
              <prop k="horizontal_anchor_point" v="1"/>
              <prop k="joinstyle" v="bevel"/>
              <prop k="name" v="circle"/>
              <prop k="offset" v="0,0"/>
              <prop k="offset_map_unit_scale" v="3x:0,0,0,0,0,0"/>
              <prop k="offset_unit" v="MM"/>
              <prop k="outline_color" v="35,35,35,255"/>
              <prop k="outline_style" v="no"/>
              <prop k="outline_width" v="0"/>
              <prop k="outline_width_map_unit_scale" v="3x:0,0,0,0,0,0"/>
              <prop k="outline_width_unit" v="MM"/>
              <prop k="scale_method" v="diameter"/>
              <prop k="size" v="0.4"/>
              <prop k="size_map_unit_scale" v="3x:0,0,0,0,0,0"/>
              <prop k="size_unit" v="MM"/>
              <prop k="vertical_anchor_point" v="1"/>
              <data_defined_properties>
                <Option type="Map">
                  <Option value="" type="QString" name="name"/>
                  <Option name="properties"/>
                  <Option value="collection" type="QString" name="type"/>
                </Option>
              </data_defined_properties>
            </layer>
          </symbol>
        </layer>
        <layer enabled="1" class="SimpleFill" pass="0" locked="0">
          <prop k="border_width_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="color" v="0,0,255,255"/>
          <prop k="joinstyle" v="bevel"/>
          <prop k="offset" v="0,0"/>
          <prop k="offset_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="offset_unit" v="MM"/>
          <prop k="outline_color" v="143,0,2,255"/>
          <prop k="outline_style" v="solid"/>
          <prop k="outline_width" v="0.26"/>
          <prop k="outline_width_unit" v="MM"/>
          <prop k="style" v="no"/>
          <data_defined_properties>
            <Option type="Map">
              <Option value="" type="QString" name="name"/>
              <Option name="properties"/>
              <Option value="collection" type="QString" name="type"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
      <symbol type="fill" name="3" force_rhr="0" clip_to_extent="1" alpha="1">
        <layer enabled="1" class="PointPatternFill" pass="0" locked="0">
          <prop k="displacement_x" v="1.2"/>
          <prop k="displacement_x_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="displacement_x_unit" v="MM"/>
          <prop k="displacement_y" v="0"/>
          <prop k="displacement_y_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="displacement_y_unit" v="MM"/>
          <prop k="distance_x" v="2.4"/>
          <prop k="distance_x_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="distance_x_unit" v="MM"/>
          <prop k="distance_y" v="2.4"/>
          <prop k="distance_y_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="distance_y_unit" v="MM"/>
          <prop k="offset_x" v="0"/>
          <prop k="offset_x_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="offset_x_unit" v="MM"/>
          <prop k="offset_y" v="0"/>
          <prop k="offset_y_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="offset_y_unit" v="MM"/>
          <prop k="outline_width_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="outline_width_unit" v="MM"/>
          <data_defined_properties>
            <Option type="Map">
              <Option value="" type="QString" name="name"/>
              <Option name="properties"/>
              <Option value="collection" type="QString" name="type"/>
            </Option>
          </data_defined_properties>
          <symbol type="marker" name="@3@0" force_rhr="0" clip_to_extent="1" alpha="1">
            <layer enabled="1" class="SimpleMarker" pass="0" locked="0">
              <prop k="angle" v="0"/>
              <prop k="color" v="0,0,255,255"/>
              <prop k="horizontal_anchor_point" v="1"/>
              <prop k="joinstyle" v="bevel"/>
              <prop k="name" v="circle"/>
              <prop k="offset" v="0,0"/>
              <prop k="offset_map_unit_scale" v="3x:0,0,0,0,0,0"/>
              <prop k="offset_unit" v="MM"/>
              <prop k="outline_color" v="0,0,255,255"/>
              <prop k="outline_style" v="solid"/>
              <prop k="outline_width" v="0.2"/>
              <prop k="outline_width_map_unit_scale" v="3x:0,0,0,0,0,0"/>
              <prop k="outline_width_unit" v="MM"/>
              <prop k="scale_method" v="diameter"/>
              <prop k="size" v="0.4"/>
              <prop k="size_map_unit_scale" v="3x:0,0,0,0,0,0"/>
              <prop k="size_unit" v="MM"/>
              <prop k="vertical_anchor_point" v="1"/>
              <data_defined_properties>
                <Option type="Map">
                  <Option value="" type="QString" name="name"/>
                  <Option name="properties"/>
                  <Option value="collection" type="QString" name="type"/>
                </Option>
              </data_defined_properties>
            </layer>
          </symbol>
        </layer>
        <layer enabled="1" class="SimpleFill" pass="0" locked="0">
          <prop k="border_width_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="color" v="0,0,255,255"/>
          <prop k="joinstyle" v="bevel"/>
          <prop k="offset" v="0,0"/>
          <prop k="offset_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="offset_unit" v="MM"/>
          <prop k="outline_color" v="0,0,255,255"/>
          <prop k="outline_style" v="solid"/>
          <prop k="outline_width" v="0.26"/>
          <prop k="outline_width_unit" v="MM"/>
          <prop k="style" v="no"/>
          <data_defined_properties>
            <Option type="Map">
              <Option value="" type="QString" name="name"/>
              <Option name="properties"/>
              <Option value="collection" type="QString" name="type"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
      <symbol type="fill" name="4" force_rhr="0" clip_to_extent="1" alpha="1">
        <layer enabled="1" class="LinePatternFill" pass="0" locked="0">
          <prop k="angle" v="0"/>
          <prop k="color" v="164,113,88,255"/>
          <prop k="distance" v="5"/>
          <prop k="distance_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="distance_unit" v="MM"/>
          <prop k="line_width" v="0.26"/>
          <prop k="line_width_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="line_width_unit" v="MM"/>
          <prop k="offset" v="0"/>
          <prop k="offset_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="offset_unit" v="MM"/>
          <prop k="outline_width_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="outline_width_unit" v="MM"/>
          <data_defined_properties>
            <Option type="Map">
              <Option value="" type="QString" name="name"/>
              <Option name="properties"/>
              <Option value="collection" type="QString" name="type"/>
            </Option>
          </data_defined_properties>
          <symbol type="line" name="@4@0" force_rhr="0" clip_to_extent="1" alpha="1">
            <layer enabled="1" class="SimpleLine" pass="0" locked="0">
              <prop k="capstyle" v="square"/>
              <prop k="customdash" v="5;2"/>
              <prop k="customdash_map_unit_scale" v="3x:0,0,0,0,0,0"/>
              <prop k="customdash_unit" v="MM"/>
              <prop k="draw_inside_polygon" v="0"/>
              <prop k="joinstyle" v="bevel"/>
              <prop k="line_color" v="164,0,2,255"/>
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
                  <Option value="" type="QString" name="name"/>
                  <Option name="properties"/>
                  <Option value="collection" type="QString" name="type"/>
                </Option>
              </data_defined_properties>
            </layer>
          </symbol>
        </layer>
        <layer enabled="1" class="SimpleFill" pass="0" locked="0">
          <prop k="border_width_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="color" v="0,0,255,255"/>
          <prop k="joinstyle" v="bevel"/>
          <prop k="offset" v="0,0"/>
          <prop k="offset_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="offset_unit" v="MM"/>
          <prop k="outline_color" v="143,0,2,255"/>
          <prop k="outline_style" v="solid"/>
          <prop k="outline_width" v="0.26"/>
          <prop k="outline_width_unit" v="MM"/>
          <prop k="style" v="no"/>
          <data_defined_properties>
            <Option type="Map">
              <Option value="" type="QString" name="name"/>
              <Option name="properties"/>
              <Option value="collection" type="QString" name="type"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
    </symbols>
  </renderer-v2>
  <labeling type="rule-based">
    <rules key="{09a22423-2570-4355-876c-82324053231f}">
      <rule scalemaxdenom="10050" key="{3029e37f-21a2-46c0-afda-5f7ee25e0a9f}" scalemindenom="1000" description="I" filter="&quot;ZABIEG&quot; in ('IA', 'IB', 'IC')">
        <settings calloutType="simple">
          <text-style textOrientation="horizontal" fontKerning="1" textColor="155,0,0,255" fontSizeMapUnitScale="3x:0,0,0,0,0,0" fontItalic="0" fontLetterSpacing="0" fieldName="&quot;ZABIEG&quot; + '\n' + &quot;DZRB_OPS&quot;+' ['+to_string(round(&quot;POW_GRAF&quot;,2))+' ha'+']'" fontUnderline="0" blendMode="0" multilineHeight="1" previewBkgrdColor="0,0,0,255" fontSizeUnit="Point" isExpression="1" fontWeight="50" fontStrikeout="0" fontWordSpacing="0" fontFamily="Noto Sans" useSubstitutions="0" allowHtml="0" textOpacity="1" fontCapitals="0" fontSize="7" namedStyle="Regular">
            <text-buffer bufferSizeUnits="MM" bufferDraw="1" bufferSizeMapUnitScale="3x:0,0,0,0,0,0" bufferColor="255,255,255,255" bufferOpacity="1" bufferNoFill="1" bufferJoinStyle="128" bufferBlendMode="0" bufferSize="0"/>
            <text-mask maskSizeMapUnitScale="3x:0,0,0,0,0,0" maskOpacity="1" maskedSymbolLayers="" maskSize="0" maskEnabled="0" maskType="0" maskSizeUnits="MM" maskJoinStyle="128"/>
            <background shapeSizeY="0" shapeOffsetMapUnitScale="3x:0,0,0,0,0,0" shapeBorderWidth="0" shapeBorderWidthUnit="MM" shapeSizeUnit="MM" shapeSizeMapUnitScale="3x:0,0,0,0,0,0" shapeBorderColor="128,128,128,255" shapeFillColor="255,255,255,255" shapeBlendMode="0" shapeSVGFile="" shapeRotationType="0" shapeOpacity="1" shapeRadiiUnit="MM" shapeJoinStyle="64" shapeDraw="0" shapeType="0" shapeOffsetY="0" shapeOffsetX="0" shapeRotation="0" shapeSizeX="0" shapeOffsetUnit="MM" shapeRadiiX="0" shapeRadiiY="0" shapeBorderWidthMapUnitScale="3x:0,0,0,0,0,0" shapeRadiiMapUnitScale="3x:0,0,0,0,0,0" shapeSizeType="0"/>
            <shadow shadowDraw="0" shadowUnder="0" shadowOffsetUnit="MM" shadowBlendMode="6" shadowRadiusAlphaOnly="0" shadowRadiusMapUnitScale="3x:0,0,0,0,0,0" shadowOffsetMapUnitScale="3x:0,0,0,0,0,0" shadowOffsetGlobal="1" shadowRadius="0" shadowOpacity="0" shadowRadiusUnit="MM" shadowColor="0,0,0,255" shadowOffsetAngle="135" shadowOffsetDist="1" shadowScale="100"/>
            <dd_properties>
              <Option type="Map">
                <Option value="" type="QString" name="name"/>
                <Option name="properties"/>
                <Option value="collection" type="QString" name="type"/>
              </Option>
            </dd_properties>
            <substitutions/>
          </text-style>
          <text-format autoWrapLength="0" rightDirectionSymbol=">" formatNumbers="0" useMaxLineLengthForAutoWrap="1" reverseDirectionSymbol="0" plussign="0" addDirectionSymbol="0" wrapChar="" multilineAlign="1" leftDirectionSymbol="&lt;" placeDirectionSymbol="0" decimals="3"/>
          <placement labelOffsetMapUnitScale="3x:0,0,0,0,0,0" layerType="UnknownGeometry" quadOffset="4" repeatDistanceMapUnitScale="3x:0,0,0,0,0,0" distMapUnitScale="3x:0,0,0,0,0,0" dist="0" fitInPolygonOnly="0" overrunDistanceUnit="MM" geometryGeneratorEnabled="0" offsetType="0" geometryGenerator="" polygonPlacementFlags="2" repeatDistanceUnits="MM" geometryGeneratorType="PointGeometry" centroidInside="1" xOffset="0" priority="5" predefinedPositionOrder="TR,TL,BR,BL,R,L,TSR,BSR" repeatDistance="0" rotationAngle="0" preserveRotation="1" overrunDistance="0" maxCurvedCharAngleIn="25" maxCurvedCharAngleOut="-25" placement="0" overrunDistanceMapUnitScale="3x:0,0,0,0,0,0" centroidWhole="0" placementFlags="10" distUnits="MM" offsetUnits="MM" yOffset="0"/>
          <rendering limitNumLabels="0" maxNumLabels="2000" obstacle="1" scaleMin="0" fontLimitPixelSize="0" upsidedownLabels="0" minFeatureSize="0" displayAll="1" scaleVisibility="0" mergeLines="0" scaleMax="0" drawLabels="1" zIndex="0" fontMaxPixelSize="10000" fontMinPixelSize="3" obstacleType="1" obstacleFactor="1" labelPerPart="0"/>
          <dd_properties>
            <Option type="Map">
              <Option value="" type="QString" name="name"/>
              <Option name="properties"/>
              <Option value="collection" type="QString" name="type"/>
            </Option>
          </dd_properties>
          <callout type="simple">
            <Option type="Map">
              <Option value="pole_of_inaccessibility" type="QString" name="anchorPoint"/>
              <Option type="Map" name="ddProperties">
                <Option value="" type="QString" name="name"/>
                <Option name="properties"/>
                <Option value="collection" type="QString" name="type"/>
              </Option>
              <Option value="false" type="bool" name="drawToAllParts"/>
              <Option value="0" type="QString" name="enabled"/>
              <Option value="point_on_exterior" type="QString" name="labelAnchorPoint"/>
              <Option value="&lt;symbol type=&quot;line&quot; name=&quot;symbol&quot; force_rhr=&quot;0&quot; clip_to_extent=&quot;1&quot; alpha=&quot;1&quot;>&lt;layer enabled=&quot;1&quot; class=&quot;SimpleLine&quot; pass=&quot;0&quot; locked=&quot;0&quot;>&lt;prop k=&quot;capstyle&quot; v=&quot;square&quot;/>&lt;prop k=&quot;customdash&quot; v=&quot;5;2&quot;/>&lt;prop k=&quot;customdash_map_unit_scale&quot; v=&quot;3x:0,0,0,0,0,0&quot;/>&lt;prop k=&quot;customdash_unit&quot; v=&quot;MM&quot;/>&lt;prop k=&quot;draw_inside_polygon&quot; v=&quot;0&quot;/>&lt;prop k=&quot;joinstyle&quot; v=&quot;bevel&quot;/>&lt;prop k=&quot;line_color&quot; v=&quot;60,60,60,255&quot;/>&lt;prop k=&quot;line_style&quot; v=&quot;solid&quot;/>&lt;prop k=&quot;line_width&quot; v=&quot;0.3&quot;/>&lt;prop k=&quot;line_width_unit&quot; v=&quot;MM&quot;/>&lt;prop k=&quot;offset&quot; v=&quot;0&quot;/>&lt;prop k=&quot;offset_map_unit_scale&quot; v=&quot;3x:0,0,0,0,0,0&quot;/>&lt;prop k=&quot;offset_unit&quot; v=&quot;MM&quot;/>&lt;prop k=&quot;ring_filter&quot; v=&quot;0&quot;/>&lt;prop k=&quot;use_custom_dash&quot; v=&quot;0&quot;/>&lt;prop k=&quot;width_map_unit_scale&quot; v=&quot;3x:0,0,0,0,0,0&quot;/>&lt;data_defined_properties>&lt;Option type=&quot;Map&quot;>&lt;Option value=&quot;&quot; type=&quot;QString&quot; name=&quot;name&quot;/>&lt;Option name=&quot;properties&quot;/>&lt;Option value=&quot;collection&quot; type=&quot;QString&quot; name=&quot;type&quot;/>&lt;/Option>&lt;/data_defined_properties>&lt;/layer>&lt;/symbol>" type="QString" name="lineSymbol"/>
              <Option value="0" type="double" name="minLength"/>
              <Option value="3x:0,0,0,0,0,0" type="QString" name="minLengthMapUnitScale"/>
              <Option value="MM" type="QString" name="minLengthUnit"/>
              <Option value="0" type="double" name="offsetFromAnchor"/>
              <Option value="3x:0,0,0,0,0,0" type="QString" name="offsetFromAnchorMapUnitScale"/>
              <Option value="MM" type="QString" name="offsetFromAnchorUnit"/>
              <Option value="0" type="double" name="offsetFromLabel"/>
              <Option value="3x:0,0,0,0,0,0" type="QString" name="offsetFromLabelMapUnitScale"/>
              <Option value="MM" type="QString" name="offsetFromLabelUnit"/>
            </Option>
          </callout>
        </settings>
      </rule>
      <rule scalemaxdenom="10050" key="{181baa87-1327-4585-81a9-be37745473c4}" scalemindenom="1000" description="zloz" filter="&quot;ZABIEG&quot; not in ('IA', 'IB', 'IC', 'CW', 'CP', 'CP-P', 'TW', 'TP')">
        <settings calloutType="simple">
          <text-style textOrientation="horizontal" fontKerning="1" textColor="0,0,163,255" fontSizeMapUnitScale="3x:0,0,0,0,0,0" fontItalic="0" fontLetterSpacing="0" fieldName="&quot;ZABIEG&quot; + '\n' + &quot;DZRB_OPS&quot;+' ['+to_string(round(&quot;POW_GRAF&quot;, 2))+' ha'+']'" fontUnderline="0" blendMode="0" multilineHeight="1" previewBkgrdColor="0,0,0,255" fontSizeUnit="Point" isExpression="1" fontWeight="50" fontStrikeout="0" fontWordSpacing="0" fontFamily="Noto Sans" useSubstitutions="0" allowHtml="0" textOpacity="1" fontCapitals="0" fontSize="7" namedStyle="Regular">
            <text-buffer bufferSizeUnits="MM" bufferDraw="1" bufferSizeMapUnitScale="3x:0,0,0,0,0,0" bufferColor="255,255,255,255" bufferOpacity="1" bufferNoFill="1" bufferJoinStyle="128" bufferBlendMode="0" bufferSize="0"/>
            <text-mask maskSizeMapUnitScale="3x:0,0,0,0,0,0" maskOpacity="1" maskedSymbolLayers="" maskSize="0" maskEnabled="0" maskType="0" maskSizeUnits="MM" maskJoinStyle="128"/>
            <background shapeSizeY="0" shapeOffsetMapUnitScale="3x:0,0,0,0,0,0" shapeBorderWidth="0" shapeBorderWidthUnit="MM" shapeSizeUnit="MM" shapeSizeMapUnitScale="3x:0,0,0,0,0,0" shapeBorderColor="128,128,128,255" shapeFillColor="255,255,255,255" shapeBlendMode="0" shapeSVGFile="" shapeRotationType="0" shapeOpacity="1" shapeRadiiUnit="MM" shapeJoinStyle="64" shapeDraw="0" shapeType="0" shapeOffsetY="0" shapeOffsetX="0" shapeRotation="0" shapeSizeX="0" shapeOffsetUnit="MM" shapeRadiiX="0" shapeRadiiY="0" shapeBorderWidthMapUnitScale="3x:0,0,0,0,0,0" shapeRadiiMapUnitScale="3x:0,0,0,0,0,0" shapeSizeType="0"/>
            <shadow shadowDraw="0" shadowUnder="0" shadowOffsetUnit="MM" shadowBlendMode="6" shadowRadiusAlphaOnly="0" shadowRadiusMapUnitScale="3x:0,0,0,0,0,0" shadowOffsetMapUnitScale="3x:0,0,0,0,0,0" shadowOffsetGlobal="1" shadowRadius="0" shadowOpacity="0" shadowRadiusUnit="MM" shadowColor="0,0,0,255" shadowOffsetAngle="135" shadowOffsetDist="1" shadowScale="100"/>
            <dd_properties>
              <Option type="Map">
                <Option value="" type="QString" name="name"/>
                <Option name="properties"/>
                <Option value="collection" type="QString" name="type"/>
              </Option>
            </dd_properties>
            <substitutions/>
          </text-style>
          <text-format autoWrapLength="0" rightDirectionSymbol=">" formatNumbers="0" useMaxLineLengthForAutoWrap="1" reverseDirectionSymbol="0" plussign="0" addDirectionSymbol="0" wrapChar="" multilineAlign="1" leftDirectionSymbol="&lt;" placeDirectionSymbol="0" decimals="3"/>
          <placement labelOffsetMapUnitScale="3x:0,0,0,0,0,0" layerType="UnknownGeometry" quadOffset="4" repeatDistanceMapUnitScale="3x:0,0,0,0,0,0" distMapUnitScale="3x:0,0,0,0,0,0" dist="0" fitInPolygonOnly="0" overrunDistanceUnit="MM" geometryGeneratorEnabled="0" offsetType="0" geometryGenerator="" polygonPlacementFlags="2" repeatDistanceUnits="MM" geometryGeneratorType="PointGeometry" centroidInside="1" xOffset="0" priority="5" predefinedPositionOrder="TR,TL,BR,BL,R,L,TSR,BSR" repeatDistance="0" rotationAngle="0" preserveRotation="1" overrunDistance="0" maxCurvedCharAngleIn="25" maxCurvedCharAngleOut="-25" placement="0" overrunDistanceMapUnitScale="3x:0,0,0,0,0,0" centroidWhole="0" placementFlags="10" distUnits="MM" offsetUnits="MM" yOffset="0"/>
          <rendering limitNumLabels="0" maxNumLabels="2000" obstacle="1" scaleMin="0" fontLimitPixelSize="0" upsidedownLabels="0" minFeatureSize="0" displayAll="1" scaleVisibility="0" mergeLines="0" scaleMax="0" drawLabels="1" zIndex="0" fontMaxPixelSize="10000" fontMinPixelSize="3" obstacleType="1" obstacleFactor="1" labelPerPart="0"/>
          <dd_properties>
            <Option type="Map">
              <Option value="" type="QString" name="name"/>
              <Option name="properties"/>
              <Option value="collection" type="QString" name="type"/>
            </Option>
          </dd_properties>
          <callout type="simple">
            <Option type="Map">
              <Option value="pole_of_inaccessibility" type="QString" name="anchorPoint"/>
              <Option type="Map" name="ddProperties">
                <Option value="" type="QString" name="name"/>
                <Option name="properties"/>
                <Option value="collection" type="QString" name="type"/>
              </Option>
              <Option value="false" type="bool" name="drawToAllParts"/>
              <Option value="0" type="QString" name="enabled"/>
              <Option value="point_on_exterior" type="QString" name="labelAnchorPoint"/>
              <Option value="&lt;symbol type=&quot;line&quot; name=&quot;symbol&quot; force_rhr=&quot;0&quot; clip_to_extent=&quot;1&quot; alpha=&quot;1&quot;>&lt;layer enabled=&quot;1&quot; class=&quot;SimpleLine&quot; pass=&quot;0&quot; locked=&quot;0&quot;>&lt;prop k=&quot;capstyle&quot; v=&quot;square&quot;/>&lt;prop k=&quot;customdash&quot; v=&quot;5;2&quot;/>&lt;prop k=&quot;customdash_map_unit_scale&quot; v=&quot;3x:0,0,0,0,0,0&quot;/>&lt;prop k=&quot;customdash_unit&quot; v=&quot;MM&quot;/>&lt;prop k=&quot;draw_inside_polygon&quot; v=&quot;0&quot;/>&lt;prop k=&quot;joinstyle&quot; v=&quot;bevel&quot;/>&lt;prop k=&quot;line_color&quot; v=&quot;60,60,60,255&quot;/>&lt;prop k=&quot;line_style&quot; v=&quot;solid&quot;/>&lt;prop k=&quot;line_width&quot; v=&quot;0.3&quot;/>&lt;prop k=&quot;line_width_unit&quot; v=&quot;MM&quot;/>&lt;prop k=&quot;offset&quot; v=&quot;0&quot;/>&lt;prop k=&quot;offset_map_unit_scale&quot; v=&quot;3x:0,0,0,0,0,0&quot;/>&lt;prop k=&quot;offset_unit&quot; v=&quot;MM&quot;/>&lt;prop k=&quot;ring_filter&quot; v=&quot;0&quot;/>&lt;prop k=&quot;use_custom_dash&quot; v=&quot;0&quot;/>&lt;prop k=&quot;width_map_unit_scale&quot; v=&quot;3x:0,0,0,0,0,0&quot;/>&lt;data_defined_properties>&lt;Option type=&quot;Map&quot;>&lt;Option value=&quot;&quot; type=&quot;QString&quot; name=&quot;name&quot;/>&lt;Option name=&quot;properties&quot;/>&lt;Option value=&quot;collection&quot; type=&quot;QString&quot; name=&quot;type&quot;/>&lt;/Option>&lt;/data_defined_properties>&lt;/layer>&lt;/symbol>" type="QString" name="lineSymbol"/>
              <Option value="0" type="double" name="minLength"/>
              <Option value="3x:0,0,0,0,0,0" type="QString" name="minLengthMapUnitScale"/>
              <Option value="MM" type="QString" name="minLengthUnit"/>
              <Option value="0" type="double" name="offsetFromAnchor"/>
              <Option value="3x:0,0,0,0,0,0" type="QString" name="offsetFromAnchorMapUnitScale"/>
              <Option value="MM" type="QString" name="offsetFromAnchorUnit"/>
              <Option value="0" type="double" name="offsetFromLabel"/>
              <Option value="3x:0,0,0,0,0,0" type="QString" name="offsetFromLabelMapUnitScale"/>
              <Option value="MM" type="QString" name="offsetFromLabelUnit"/>
            </Option>
          </callout>
        </settings>
      </rule>
    </rules>
  </labeling>
  <customproperties>
    <property key="dualview/previewExpressions">
      <value>POZAEWID</value>
    </property>
    <property value="0" key="embeddedWidgets/count"/>
    <property key="variableNames"/>
    <property key="variableValues"/>
  </customproperties>
  <blendMode>0</blendMode>
  <featureBlendMode>0</featureBlendMode>
  <layerOpacity>1</layerOpacity>
  <SingleCategoryDiagramRenderer attributeLegend="1" diagramType="Histogram">
    <DiagramCategory spacingUnit="MM" diagramOrientation="Up" height="15" barWidth="5" enabled="0" scaleBasedVisibility="0" direction="1" backgroundColor="#ffffff" penWidth="0" minimumSize="0" spacing="0" opacity="1" penAlpha="255" scaleDependency="Area" maxScaleDenominator="1e+08" width="15" backgroundAlpha="255" labelPlacementMethod="XHeight" spacingUnitScale="3x:0,0,0,0,0,0" lineSizeScale="3x:0,0,0,0,0,0" sizeScale="3x:0,0,0,0,0,0" showAxis="0" minScaleDenominator="0" sizeType="MM" lineSizeType="MM" penColor="#000000" rotationOffset="270">
      <fontProperties description="Noto Sans,11,-1,5,50,0,0,0,0,0,Regular" style="Regular"/>
      <attribute label="" color="#000000" field=""/>
      <axisSymbol>
        <symbol type="line" name="" force_rhr="0" clip_to_extent="1" alpha="1">
          <layer enabled="1" class="SimpleLine" pass="0" locked="0">
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
                <Option value="" type="QString" name="name"/>
                <Option name="properties"/>
                <Option value="collection" type="QString" name="type"/>
              </Option>
            </data_defined_properties>
          </layer>
        </symbol>
      </axisSymbol>
    </DiagramCategory>
  </SingleCategoryDiagramRenderer>
  <DiagramLayerSettings showAll="1" obstacle="0" priority="0" zIndex="0" linePlacementFlags="18" dist="0" placement="1">
    <properties>
      <Option type="Map">
        <Option value="" type="QString" name="name"/>
        <Option name="properties"/>
        <Option value="collection" type="QString" name="type"/>
      </Option>
    </properties>
  </DiagramLayerSettings>
  <geometryOptions removeDuplicateNodes="0" geometryPrecision="0">
    <activeChecks/>
    <checkConfiguration type="Map">
      <Option type="Map" name="QgsGeometryGapCheck">
        <Option value="0" type="double" name="allowedGapsBuffer"/>
        <Option value="false" type="bool" name="allowedGapsEnabled"/>
        <Option value="" type="QString" name="allowedGapsLayer"/>
      </Option>
    </checkConfiguration>
  </geometryOptions>
  <referencedLayers/>
  <referencingLayers/>
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
    <field name="GRP">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="COUNTY_L">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="ODDZ">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="WYDZ">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="ADR_LES">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="POW_GRAF">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="POZAEWID">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="ST_ADR_LES">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="ST_ODDZ">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="ST_WYDZ">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="L_EWID">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="UDZIAL">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="GAT">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="WIEK">
      <editWidget type="Range">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="ZADRZEW">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="POW_WYDZ">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="TYP_POW">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="STRUKTUR">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="SLMN_KOL">
      <editWidget type="Range">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="STL">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="ZABIEG">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="POW_ZAB">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="ODNOW">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="POW_ODN">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="AGROT">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="PIEL">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="PRZEST">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="INNE">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="DZ_ZRB">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="DZRB_OPS">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
  </fieldConfiguration>
  <aliases>
    <alias name="" field="COUNTY" index="0"/>
    <alias name="" field="DISTRICT" index="1"/>
    <alias name="" field="MUNICIP" index="2"/>
    <alias name="" field="COMMUNITY" index="3"/>
    <alias name="" field="GRP" index="4"/>
    <alias name="" field="COUNTY_L" index="5"/>
    <alias name="" field="ODDZ" index="6"/>
    <alias name="" field="WYDZ" index="7"/>
    <alias name="" field="ADR_LES" index="8"/>
    <alias name="" field="POW_GRAF" index="9"/>
    <alias name="" field="POZAEWID" index="10"/>
    <alias name="" field="ST_ADR_LES" index="11"/>
    <alias name="" field="ST_ODDZ" index="12"/>
    <alias name="" field="ST_WYDZ" index="13"/>
    <alias name="" field="L_EWID" index="14"/>
    <alias name="" field="UDZIAL" index="15"/>
    <alias name="" field="GAT" index="16"/>
    <alias name="" field="WIEK" index="17"/>
    <alias name="" field="ZADRZEW" index="18"/>
    <alias name="" field="POW_WYDZ" index="19"/>
    <alias name="" field="TYP_POW" index="20"/>
    <alias name="" field="STRUKTUR" index="21"/>
    <alias name="" field="SLMN_KOL" index="22"/>
    <alias name="" field="STL" index="23"/>
    <alias name="" field="ZABIEG" index="24"/>
    <alias name="" field="POW_ZAB" index="25"/>
    <alias name="" field="ODNOW" index="26"/>
    <alias name="" field="POW_ODN" index="27"/>
    <alias name="" field="AGROT" index="28"/>
    <alias name="" field="PIEL" index="29"/>
    <alias name="" field="PRZEST" index="30"/>
    <alias name="" field="INNE" index="31"/>
    <alias name="" field="DZ_ZRB" index="32"/>
    <alias name="" field="DZRB_OPS" index="33"/>
  </aliases>
  <excludeAttributesWMS/>
  <excludeAttributesWFS/>
  <defaults>
    <default applyOnUpdate="0" expression="" field="COUNTY"/>
    <default applyOnUpdate="0" expression="" field="DISTRICT"/>
    <default applyOnUpdate="0" expression="" field="MUNICIP"/>
    <default applyOnUpdate="0" expression="" field="COMMUNITY"/>
    <default applyOnUpdate="0" expression="" field="GRP"/>
    <default applyOnUpdate="0" expression="" field="COUNTY_L"/>
    <default applyOnUpdate="0" expression="" field="ODDZ"/>
    <default applyOnUpdate="0" expression="" field="WYDZ"/>
    <default applyOnUpdate="0" expression="" field="ADR_LES"/>
    <default applyOnUpdate="0" expression="" field="POW_GRAF"/>
    <default applyOnUpdate="0" expression="" field="POZAEWID"/>
    <default applyOnUpdate="0" expression="" field="ST_ADR_LES"/>
    <default applyOnUpdate="0" expression="" field="ST_ODDZ"/>
    <default applyOnUpdate="0" expression="" field="ST_WYDZ"/>
    <default applyOnUpdate="0" expression="" field="L_EWID"/>
    <default applyOnUpdate="0" expression="" field="UDZIAL"/>
    <default applyOnUpdate="0" expression="" field="GAT"/>
    <default applyOnUpdate="0" expression="" field="WIEK"/>
    <default applyOnUpdate="0" expression="" field="ZADRZEW"/>
    <default applyOnUpdate="0" expression="" field="POW_WYDZ"/>
    <default applyOnUpdate="0" expression="" field="TYP_POW"/>
    <default applyOnUpdate="0" expression="" field="STRUKTUR"/>
    <default applyOnUpdate="0" expression="" field="SLMN_KOL"/>
    <default applyOnUpdate="0" expression="" field="STL"/>
    <default applyOnUpdate="0" expression="" field="ZABIEG"/>
    <default applyOnUpdate="0" expression="" field="POW_ZAB"/>
    <default applyOnUpdate="0" expression="" field="ODNOW"/>
    <default applyOnUpdate="0" expression="" field="POW_ODN"/>
    <default applyOnUpdate="0" expression="" field="AGROT"/>
    <default applyOnUpdate="0" expression="" field="PIEL"/>
    <default applyOnUpdate="0" expression="" field="PRZEST"/>
    <default applyOnUpdate="0" expression="" field="INNE"/>
    <default applyOnUpdate="0" expression="" field="DZ_ZRB"/>
    <default applyOnUpdate="0" expression="" field="DZRB_OPS"/>
  </defaults>
  <constraints>
    <constraint unique_strength="0" notnull_strength="0" constraints="0" exp_strength="0" field="COUNTY"/>
    <constraint unique_strength="0" notnull_strength="0" constraints="0" exp_strength="0" field="DISTRICT"/>
    <constraint unique_strength="0" notnull_strength="0" constraints="0" exp_strength="0" field="MUNICIP"/>
    <constraint unique_strength="0" notnull_strength="0" constraints="0" exp_strength="0" field="COMMUNITY"/>
    <constraint unique_strength="0" notnull_strength="0" constraints="0" exp_strength="0" field="GRP"/>
    <constraint unique_strength="0" notnull_strength="0" constraints="0" exp_strength="0" field="COUNTY_L"/>
    <constraint unique_strength="0" notnull_strength="0" constraints="0" exp_strength="0" field="ODDZ"/>
    <constraint unique_strength="0" notnull_strength="0" constraints="0" exp_strength="0" field="WYDZ"/>
    <constraint unique_strength="0" notnull_strength="0" constraints="0" exp_strength="0" field="ADR_LES"/>
    <constraint unique_strength="0" notnull_strength="0" constraints="0" exp_strength="0" field="POW_GRAF"/>
    <constraint unique_strength="0" notnull_strength="0" constraints="0" exp_strength="0" field="POZAEWID"/>
    <constraint unique_strength="0" notnull_strength="0" constraints="0" exp_strength="0" field="ST_ADR_LES"/>
    <constraint unique_strength="0" notnull_strength="0" constraints="0" exp_strength="0" field="ST_ODDZ"/>
    <constraint unique_strength="0" notnull_strength="0" constraints="0" exp_strength="0" field="ST_WYDZ"/>
    <constraint unique_strength="0" notnull_strength="0" constraints="0" exp_strength="0" field="L_EWID"/>
    <constraint unique_strength="0" notnull_strength="0" constraints="0" exp_strength="0" field="UDZIAL"/>
    <constraint unique_strength="0" notnull_strength="0" constraints="0" exp_strength="0" field="GAT"/>
    <constraint unique_strength="0" notnull_strength="0" constraints="0" exp_strength="0" field="WIEK"/>
    <constraint unique_strength="0" notnull_strength="0" constraints="0" exp_strength="0" field="ZADRZEW"/>
    <constraint unique_strength="0" notnull_strength="0" constraints="0" exp_strength="0" field="POW_WYDZ"/>
    <constraint unique_strength="0" notnull_strength="0" constraints="0" exp_strength="0" field="TYP_POW"/>
    <constraint unique_strength="0" notnull_strength="0" constraints="0" exp_strength="0" field="STRUKTUR"/>
    <constraint unique_strength="0" notnull_strength="0" constraints="0" exp_strength="0" field="SLMN_KOL"/>
    <constraint unique_strength="0" notnull_strength="0" constraints="0" exp_strength="0" field="STL"/>
    <constraint unique_strength="0" notnull_strength="0" constraints="0" exp_strength="0" field="ZABIEG"/>
    <constraint unique_strength="0" notnull_strength="0" constraints="0" exp_strength="0" field="POW_ZAB"/>
    <constraint unique_strength="0" notnull_strength="0" constraints="0" exp_strength="0" field="ODNOW"/>
    <constraint unique_strength="0" notnull_strength="0" constraints="0" exp_strength="0" field="POW_ODN"/>
    <constraint unique_strength="0" notnull_strength="0" constraints="0" exp_strength="0" field="AGROT"/>
    <constraint unique_strength="0" notnull_strength="0" constraints="0" exp_strength="0" field="PIEL"/>
    <constraint unique_strength="0" notnull_strength="0" constraints="0" exp_strength="0" field="PRZEST"/>
    <constraint unique_strength="0" notnull_strength="0" constraints="0" exp_strength="0" field="INNE"/>
    <constraint unique_strength="0" notnull_strength="0" constraints="0" exp_strength="0" field="DZ_ZRB"/>
    <constraint unique_strength="0" notnull_strength="0" constraints="0" exp_strength="0" field="DZRB_OPS"/>
  </constraints>
  <constraintExpressions>
    <constraint desc="" exp="" field="COUNTY"/>
    <constraint desc="" exp="" field="DISTRICT"/>
    <constraint desc="" exp="" field="MUNICIP"/>
    <constraint desc="" exp="" field="COMMUNITY"/>
    <constraint desc="" exp="" field="GRP"/>
    <constraint desc="" exp="" field="COUNTY_L"/>
    <constraint desc="" exp="" field="ODDZ"/>
    <constraint desc="" exp="" field="WYDZ"/>
    <constraint desc="" exp="" field="ADR_LES"/>
    <constraint desc="" exp="" field="POW_GRAF"/>
    <constraint desc="" exp="" field="POZAEWID"/>
    <constraint desc="" exp="" field="ST_ADR_LES"/>
    <constraint desc="" exp="" field="ST_ODDZ"/>
    <constraint desc="" exp="" field="ST_WYDZ"/>
    <constraint desc="" exp="" field="L_EWID"/>
    <constraint desc="" exp="" field="UDZIAL"/>
    <constraint desc="" exp="" field="GAT"/>
    <constraint desc="" exp="" field="WIEK"/>
    <constraint desc="" exp="" field="ZADRZEW"/>
    <constraint desc="" exp="" field="POW_WYDZ"/>
    <constraint desc="" exp="" field="TYP_POW"/>
    <constraint desc="" exp="" field="STRUKTUR"/>
    <constraint desc="" exp="" field="SLMN_KOL"/>
    <constraint desc="" exp="" field="STL"/>
    <constraint desc="" exp="" field="ZABIEG"/>
    <constraint desc="" exp="" field="POW_ZAB"/>
    <constraint desc="" exp="" field="ODNOW"/>
    <constraint desc="" exp="" field="POW_ODN"/>
    <constraint desc="" exp="" field="AGROT"/>
    <constraint desc="" exp="" field="PIEL"/>
    <constraint desc="" exp="" field="PRZEST"/>
    <constraint desc="" exp="" field="INNE"/>
    <constraint desc="" exp="" field="DZ_ZRB"/>
    <constraint desc="" exp="" field="DZRB_OPS"/>
  </constraintExpressions>
  <expressionfields/>
  <attributeactions>
    <defaultAction value="{00000000-0000-0000-0000-000000000000}" key="Canvas"/>
  </attributeactions>
  <attributetableconfig sortExpression="&quot;POW_GRAF&quot;" sortOrder="1" actionWidgetStyle="dropDown">
    <columns>
      <column type="field" name="COUNTY" hidden="0" width="-1"/>
      <column type="field" name="DISTRICT" hidden="0" width="-1"/>
      <column type="field" name="MUNICIP" hidden="0" width="-1"/>
      <column type="field" name="COMMUNITY" hidden="0" width="-1"/>
      <column type="field" name="GRP" hidden="0" width="-1"/>
      <column type="field" name="COUNTY_L" hidden="0" width="-1"/>
      <column type="field" name="ODDZ" hidden="0" width="-1"/>
      <column type="field" name="WYDZ" hidden="0" width="-1"/>
      <column type="field" name="ADR_LES" hidden="0" width="-1"/>
      <column type="field" name="POW_GRAF" hidden="0" width="-1"/>
      <column type="field" name="POZAEWID" hidden="0" width="-1"/>
      <column type="field" name="ST_ADR_LES" hidden="0" width="-1"/>
      <column type="field" name="ST_ODDZ" hidden="0" width="-1"/>
      <column type="field" name="ST_WYDZ" hidden="0" width="-1"/>
      <column type="field" name="L_EWID" hidden="0" width="-1"/>
      <column type="field" name="UDZIAL" hidden="0" width="-1"/>
      <column type="field" name="GAT" hidden="0" width="-1"/>
      <column type="field" name="WIEK" hidden="0" width="-1"/>
      <column type="field" name="ZADRZEW" hidden="0" width="-1"/>
      <column type="field" name="POW_WYDZ" hidden="0" width="-1"/>
      <column type="field" name="TYP_POW" hidden="0" width="-1"/>
      <column type="field" name="STRUKTUR" hidden="0" width="-1"/>
      <column type="field" name="SLMN_KOL" hidden="0" width="-1"/>
      <column type="field" name="STL" hidden="0" width="-1"/>
      <column type="field" name="ZABIEG" hidden="0" width="-1"/>
      <column type="field" name="POW_ZAB" hidden="0" width="-1"/>
      <column type="field" name="ODNOW" hidden="0" width="-1"/>
      <column type="field" name="POW_ODN" hidden="0" width="-1"/>
      <column type="field" name="AGROT" hidden="0" width="-1"/>
      <column type="field" name="PIEL" hidden="0" width="-1"/>
      <column type="field" name="PRZEST" hidden="0" width="-1"/>
      <column type="field" name="INNE" hidden="0" width="-1"/>
      <column type="field" name="DZ_ZRB" hidden="0" width="-1"/>
      <column type="actions" hidden="1" width="-1"/>
      <column type="field" name="DZRB_OPS" hidden="0" width="-1"/>
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
    <field name="ADR_LES" editable="1"/>
    <field name="AGROT" editable="1"/>
    <field name="COMMUNITY" editable="1"/>
    <field name="COUNTY" editable="1"/>
    <field name="COUNTY_L" editable="1"/>
    <field name="DISTRICT" editable="1"/>
    <field name="DZRB_OPS" editable="1"/>
    <field name="DZ_ZRB" editable="1"/>
    <field name="GAT" editable="1"/>
    <field name="GRP" editable="1"/>
    <field name="INNE" editable="1"/>
    <field name="L_EWID" editable="1"/>
    <field name="MUNICIP" editable="1"/>
    <field name="ODDZ" editable="1"/>
    <field name="ODNOW" editable="1"/>
    <field name="PIEL" editable="1"/>
    <field name="POW_GRAF" editable="1"/>
    <field name="POW_ODN" editable="1"/>
    <field name="POW_WYDZ" editable="1"/>
    <field name="POW_ZAB" editable="1"/>
    <field name="POZAEWID" editable="1"/>
    <field name="PRZEST" editable="1"/>
    <field name="SLMN_KOL" editable="1"/>
    <field name="STL" editable="1"/>
    <field name="STRUKTUR" editable="1"/>
    <field name="ST_ADR_LES" editable="1"/>
    <field name="ST_ODDZ" editable="1"/>
    <field name="ST_WYDZ" editable="1"/>
    <field name="TYP_POW" editable="1"/>
    <field name="UDZIAL" editable="1"/>
    <field name="WIEK" editable="1"/>
    <field name="WYDZ" editable="1"/>
    <field name="ZABIEG" editable="1"/>
    <field name="ZADRZEW" editable="1"/>
  </editable>
  <labelOnTop>
    <field name="ADR_LES" labelOnTop="0"/>
    <field name="AGROT" labelOnTop="0"/>
    <field name="COMMUNITY" labelOnTop="0"/>
    <field name="COUNTY" labelOnTop="0"/>
    <field name="COUNTY_L" labelOnTop="0"/>
    <field name="DISTRICT" labelOnTop="0"/>
    <field name="DZRB_OPS" labelOnTop="0"/>
    <field name="DZ_ZRB" labelOnTop="0"/>
    <field name="GAT" labelOnTop="0"/>
    <field name="GRP" labelOnTop="0"/>
    <field name="INNE" labelOnTop="0"/>
    <field name="L_EWID" labelOnTop="0"/>
    <field name="MUNICIP" labelOnTop="0"/>
    <field name="ODDZ" labelOnTop="0"/>
    <field name="ODNOW" labelOnTop="0"/>
    <field name="PIEL" labelOnTop="0"/>
    <field name="POW_GRAF" labelOnTop="0"/>
    <field name="POW_ODN" labelOnTop="0"/>
    <field name="POW_WYDZ" labelOnTop="0"/>
    <field name="POW_ZAB" labelOnTop="0"/>
    <field name="POZAEWID" labelOnTop="0"/>
    <field name="PRZEST" labelOnTop="0"/>
    <field name="SLMN_KOL" labelOnTop="0"/>
    <field name="STL" labelOnTop="0"/>
    <field name="STRUKTUR" labelOnTop="0"/>
    <field name="ST_ADR_LES" labelOnTop="0"/>
    <field name="ST_ODDZ" labelOnTop="0"/>
    <field name="ST_WYDZ" labelOnTop="0"/>
    <field name="TYP_POW" labelOnTop="0"/>
    <field name="UDZIAL" labelOnTop="0"/>
    <field name="WIEK" labelOnTop="0"/>
    <field name="WYDZ" labelOnTop="0"/>
    <field name="ZABIEG" labelOnTop="0"/>
    <field name="ZADRZEW" labelOnTop="0"/>
  </labelOnTop>
  <dataDefinedFieldProperties/>
  <widgets/>
  <previewExpression>"POZAEWID"</previewExpression>
  <mapTip></mapTip>
  <layerGeometryType>2</layerGeometryType>
</qgis>
