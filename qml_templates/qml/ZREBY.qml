<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis styleCategories="AllStyleCategories" simplifyDrawingHints="1" labelsEnabled="1" simplifyAlgorithm="0" simplifyMaxScale="1" maxScale="0" simplifyLocal="1" readOnly="0" hasScaleBasedVisibilityFlag="1" version="3.14.1-Pi" minScale="10050" simplifyDrawingTol="1">
  <flags>
    <Identifiable>1</Identifiable>
    <Removable>1</Removable>
    <Searchable>1</Searchable>
  </flags>
  <temporal startExpression="" durationField="" mode="0" enabled="0" endField="" durationUnit="min" fixedDuration="0" accumulate="0" startField="" endExpression="">
    <fixedRange>
      <start></start>
      <end></end>
    </fixedRange>
  </temporal>
  <renderer-v2 forceraster="0" enableorderby="0" symbollevels="0" type="RuleRenderer">
    <rules key="{ca6f00eb-fc34-433d-93b0-30342a0601fb}">
      <rule filter=" &quot;DZ_ZRB&quot; = 'Ipocz'" label="Rębnia I (początek planu)" key="{551d15fe-e993-4074-8244-0759bbc63f8c}" symbol="0"/>
      <rule filter="&quot;DZ_ZRB&quot; = 'Ikon'" label="Rębnia I (koniec planu)" key="{a41317cf-ff56-4010-adb3-0a68faae889c}" symbol="1"/>
      <rule filter="&quot;DZ_ZRB&quot; = 'I'" label="Rębnia I" key="{4269f41d-a320-4e83-94f4-31d3d17acf3f}" symbol="2"/>
      <rule filter="&quot;DZ_ZRB&quot; = 'zloz'" label="Rębnie złożone" key="{7ef46ea0-83aa-4eea-a3d8-7a2c54d89b49}" symbol="3"/>
      <rule filter="&quot;DZ_ZRB&quot; = 'Ioslo'" label="Rębnia I (dz. zrębowe osłonowe pozostające do trzebierzy)" key="{987e6b28-b0db-4b46-8d1a-a845db032818}" symbol="4"/>
    </rules>
    <symbols>
      <symbol clip_to_extent="1" name="0" force_rhr="0" type="fill" alpha="1">
        <layer pass="0" class="LinePatternFill" enabled="1" locked="0">
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
              <Option name="name" type="QString" value=""/>
              <Option name="properties"/>
              <Option name="type" type="QString" value="collection"/>
            </Option>
          </data_defined_properties>
          <symbol clip_to_extent="1" name="@0@0" force_rhr="0" type="line" alpha="1">
            <layer pass="0" class="SimpleLine" enabled="1" locked="0">
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
                  <Option name="name" type="QString" value=""/>
                  <Option name="properties"/>
                  <Option name="type" type="QString" value="collection"/>
                </Option>
              </data_defined_properties>
            </layer>
          </symbol>
        </layer>
        <layer pass="0" class="SimpleFill" enabled="1" locked="0">
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
              <Option name="name" type="QString" value=""/>
              <Option name="properties"/>
              <Option name="type" type="QString" value="collection"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
      <symbol clip_to_extent="1" name="1" force_rhr="0" type="fill" alpha="1">
        <layer pass="0" class="LinePatternFill" enabled="1" locked="0">
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
              <Option name="name" type="QString" value=""/>
              <Option name="properties"/>
              <Option name="type" type="QString" value="collection"/>
            </Option>
          </data_defined_properties>
          <symbol clip_to_extent="1" name="@1@0" force_rhr="0" type="line" alpha="1">
            <layer pass="0" class="SimpleLine" enabled="1" locked="0">
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
                  <Option name="name" type="QString" value=""/>
                  <Option name="properties"/>
                  <Option name="type" type="QString" value="collection"/>
                </Option>
              </data_defined_properties>
            </layer>
          </symbol>
        </layer>
        <layer pass="0" class="SimpleFill" enabled="1" locked="0">
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
              <Option name="name" type="QString" value=""/>
              <Option name="properties"/>
              <Option name="type" type="QString" value="collection"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
      <symbol clip_to_extent="1" name="2" force_rhr="0" type="fill" alpha="1">
        <layer pass="0" class="PointPatternFill" enabled="1" locked="0">
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
              <Option name="name" type="QString" value=""/>
              <Option name="properties"/>
              <Option name="type" type="QString" value="collection"/>
            </Option>
          </data_defined_properties>
          <symbol clip_to_extent="1" name="@2@0" force_rhr="0" type="marker" alpha="1">
            <layer pass="0" class="SimpleMarker" enabled="1" locked="0">
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
                  <Option name="name" type="QString" value=""/>
                  <Option name="properties"/>
                  <Option name="type" type="QString" value="collection"/>
                </Option>
              </data_defined_properties>
            </layer>
          </symbol>
        </layer>
        <layer pass="0" class="SimpleFill" enabled="1" locked="0">
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
              <Option name="name" type="QString" value=""/>
              <Option name="properties"/>
              <Option name="type" type="QString" value="collection"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
      <symbol clip_to_extent="1" name="3" force_rhr="0" type="fill" alpha="1">
        <layer pass="0" class="PointPatternFill" enabled="1" locked="0">
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
              <Option name="name" type="QString" value=""/>
              <Option name="properties"/>
              <Option name="type" type="QString" value="collection"/>
            </Option>
          </data_defined_properties>
          <symbol clip_to_extent="1" name="@3@0" force_rhr="0" type="marker" alpha="1">
            <layer pass="0" class="SimpleMarker" enabled="1" locked="0">
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
                  <Option name="name" type="QString" value=""/>
                  <Option name="properties"/>
                  <Option name="type" type="QString" value="collection"/>
                </Option>
              </data_defined_properties>
            </layer>
          </symbol>
        </layer>
        <layer pass="0" class="SimpleFill" enabled="1" locked="0">
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
              <Option name="name" type="QString" value=""/>
              <Option name="properties"/>
              <Option name="type" type="QString" value="collection"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
      <symbol clip_to_extent="1" name="4" force_rhr="0" type="fill" alpha="1">
        <layer pass="0" class="LinePatternFill" enabled="1" locked="0">
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
              <Option name="name" type="QString" value=""/>
              <Option name="properties"/>
              <Option name="type" type="QString" value="collection"/>
            </Option>
          </data_defined_properties>
          <symbol clip_to_extent="1" name="@4@0" force_rhr="0" type="line" alpha="1">
            <layer pass="0" class="SimpleLine" enabled="1" locked="0">
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
                  <Option name="name" type="QString" value=""/>
                  <Option name="properties"/>
                  <Option name="type" type="QString" value="collection"/>
                </Option>
              </data_defined_properties>
            </layer>
          </symbol>
        </layer>
        <layer pass="0" class="SimpleFill" enabled="1" locked="0">
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
              <Option name="name" type="QString" value=""/>
              <Option name="properties"/>
              <Option name="type" type="QString" value="collection"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
    </symbols>
  </renderer-v2>
  <labeling type="rule-based">
    <rules key="{33e4e9b6-e41a-47dd-8653-18064e61ad9d}">
      <rule description="I" scalemindenom="1000" filter="&quot;ZABIEG&quot; in ('IA', 'IB', 'IC')" scalemaxdenom="10050" key="{5fec1985-c9df-48f7-b23c-355e1f0d7936}">
        <settings calloutType="simple">
          <text-style fontUnderline="0" fontWeight="50" fontSize="7" fontLetterSpacing="0" fontKerning="1" textColor="155,0,0,255" textOrientation="horizontal" namedStyle="Regular" fontStrikeout="0" fieldName="&quot;ZABIEG&quot; + '\n' + &quot;DZRB_OPS&quot;+' ['+to_string(round(&quot;POW_GRAF&quot;,2))+' ha'+']'" useSubstitutions="0" fontItalic="0" fontSizeMapUnitScale="3x:0,0,0,0,0,0" previewBkgrdColor="0,0,0,255" fontWordSpacing="0" fontSizeUnit="Point" textOpacity="1" fontCapitals="0" fontFamily="Noto Sans" allowHtml="0" blendMode="0" multilineHeight="1" isExpression="1">
            <text-buffer bufferSizeUnits="MM" bufferBlendMode="0" bufferSize="0" bufferColor="255,255,255,255" bufferNoFill="1" bufferJoinStyle="128" bufferDraw="1" bufferOpacity="1" bufferSizeMapUnitScale="3x:0,0,0,0,0,0"/>
            <text-mask maskEnabled="0" maskType="0" maskSize="0" maskOpacity="1" maskJoinStyle="128" maskSizeUnits="MM" maskedSymbolLayers="" maskSizeMapUnitScale="3x:0,0,0,0,0,0"/>
            <background shapeSizeMapUnitScale="3x:0,0,0,0,0,0" shapeSizeX="0" shapeRadiiX="0" shapeJoinStyle="64" shapeRotation="0" shapeRadiiMapUnitScale="3x:0,0,0,0,0,0" shapeBorderWidth="0" shapeSizeType="0" shapeOffsetY="0" shapeFillColor="255,255,255,255" shapeOffsetUnit="MM" shapeBorderWidthUnit="MM" shapeBlendMode="0" shapeOffsetMapUnitScale="3x:0,0,0,0,0,0" shapeBorderColor="128,128,128,255" shapeRadiiUnit="MM" shapeRotationType="0" shapeBorderWidthMapUnitScale="3x:0,0,0,0,0,0" shapeSVGFile="" shapeOffsetX="0" shapeOpacity="1" shapeSizeY="0" shapeRadiiY="0" shapeDraw="0" shapeSizeUnit="MM" shapeType="0"/>
            <shadow shadowRadiusUnit="MM" shadowScale="100" shadowOffsetDist="1" shadowOffsetGlobal="1" shadowRadiusAlphaOnly="0" shadowUnder="0" shadowOffsetAngle="135" shadowDraw="0" shadowRadius="0" shadowOpacity="0" shadowBlendMode="6" shadowRadiusMapUnitScale="3x:0,0,0,0,0,0" shadowOffsetMapUnitScale="3x:0,0,0,0,0,0" shadowColor="0,0,0,255" shadowOffsetUnit="MM"/>
            <dd_properties>
              <Option type="Map">
                <Option name="name" type="QString" value=""/>
                <Option name="properties"/>
                <Option name="type" type="QString" value="collection"/>
              </Option>
            </dd_properties>
            <substitutions/>
          </text-style>
          <text-format wrapChar="" addDirectionSymbol="0" decimals="3" reverseDirectionSymbol="0" multilineAlign="1" useMaxLineLengthForAutoWrap="1" leftDirectionSymbol="&lt;" placeDirectionSymbol="0" formatNumbers="0" plussign="0" rightDirectionSymbol=">" autoWrapLength="0"/>
          <placement layerType="UnknownGeometry" repeatDistance="0" offsetType="0" repeatDistanceUnits="MM" fitInPolygonOnly="0" xOffset="0" dist="0" placement="0" repeatDistanceMapUnitScale="3x:0,0,0,0,0,0" geometryGenerator="" labelOffsetMapUnitScale="3x:0,0,0,0,0,0" yOffset="0" quadOffset="4" geometryGeneratorType="PointGeometry" maxCurvedCharAngleIn="25" offsetUnits="MM" polygonPlacementFlags="2" rotationAngle="0" centroidWhole="0" geometryGeneratorEnabled="0" distUnits="MM" preserveRotation="1" maxCurvedCharAngleOut="-25" predefinedPositionOrder="TR,TL,BR,BL,R,L,TSR,BSR" placementFlags="10" distMapUnitScale="3x:0,0,0,0,0,0" overrunDistanceUnit="MM" centroidInside="1" overrunDistanceMapUnitScale="3x:0,0,0,0,0,0" priority="5" overrunDistance="0"/>
          <rendering obstacle="1" fontLimitPixelSize="0" scaleMin="0" mergeLines="0" labelPerPart="0" obstacleFactor="1" scaleMax="0" maxNumLabels="2000" minFeatureSize="0" upsidedownLabels="0" displayAll="1" limitNumLabels="0" fontMinPixelSize="3" drawLabels="1" zIndex="0" scaleVisibility="0" obstacleType="1" fontMaxPixelSize="10000"/>
          <dd_properties>
            <Option type="Map">
              <Option name="name" type="QString" value=""/>
              <Option name="properties"/>
              <Option name="type" type="QString" value="collection"/>
            </Option>
          </dd_properties>
          <callout type="simple">
            <Option type="Map">
              <Option name="anchorPoint" type="QString" value="pole_of_inaccessibility"/>
              <Option name="ddProperties" type="Map">
                <Option name="name" type="QString" value=""/>
                <Option name="properties"/>
                <Option name="type" type="QString" value="collection"/>
              </Option>
              <Option name="drawToAllParts" type="bool" value="false"/>
              <Option name="enabled" type="QString" value="0"/>
              <Option name="labelAnchorPoint" type="QString" value="point_on_exterior"/>
              <Option name="lineSymbol" type="QString" value="&lt;symbol clip_to_extent=&quot;1&quot; name=&quot;symbol&quot; force_rhr=&quot;0&quot; type=&quot;line&quot; alpha=&quot;1&quot;>&lt;layer pass=&quot;0&quot; class=&quot;SimpleLine&quot; enabled=&quot;1&quot; locked=&quot;0&quot;>&lt;prop k=&quot;capstyle&quot; v=&quot;square&quot;/>&lt;prop k=&quot;customdash&quot; v=&quot;5;2&quot;/>&lt;prop k=&quot;customdash_map_unit_scale&quot; v=&quot;3x:0,0,0,0,0,0&quot;/>&lt;prop k=&quot;customdash_unit&quot; v=&quot;MM&quot;/>&lt;prop k=&quot;draw_inside_polygon&quot; v=&quot;0&quot;/>&lt;prop k=&quot;joinstyle&quot; v=&quot;bevel&quot;/>&lt;prop k=&quot;line_color&quot; v=&quot;60,60,60,255&quot;/>&lt;prop k=&quot;line_style&quot; v=&quot;solid&quot;/>&lt;prop k=&quot;line_width&quot; v=&quot;0.3&quot;/>&lt;prop k=&quot;line_width_unit&quot; v=&quot;MM&quot;/>&lt;prop k=&quot;offset&quot; v=&quot;0&quot;/>&lt;prop k=&quot;offset_map_unit_scale&quot; v=&quot;3x:0,0,0,0,0,0&quot;/>&lt;prop k=&quot;offset_unit&quot; v=&quot;MM&quot;/>&lt;prop k=&quot;ring_filter&quot; v=&quot;0&quot;/>&lt;prop k=&quot;use_custom_dash&quot; v=&quot;0&quot;/>&lt;prop k=&quot;width_map_unit_scale&quot; v=&quot;3x:0,0,0,0,0,0&quot;/>&lt;data_defined_properties>&lt;Option type=&quot;Map&quot;>&lt;Option name=&quot;name&quot; type=&quot;QString&quot; value=&quot;&quot;/>&lt;Option name=&quot;properties&quot;/>&lt;Option name=&quot;type&quot; type=&quot;QString&quot; value=&quot;collection&quot;/>&lt;/Option>&lt;/data_defined_properties>&lt;/layer>&lt;/symbol>"/>
              <Option name="minLength" type="double" value="0"/>
              <Option name="minLengthMapUnitScale" type="QString" value="3x:0,0,0,0,0,0"/>
              <Option name="minLengthUnit" type="QString" value="MM"/>
              <Option name="offsetFromAnchor" type="double" value="0"/>
              <Option name="offsetFromAnchorMapUnitScale" type="QString" value="3x:0,0,0,0,0,0"/>
              <Option name="offsetFromAnchorUnit" type="QString" value="MM"/>
              <Option name="offsetFromLabel" type="double" value="0"/>
              <Option name="offsetFromLabelMapUnitScale" type="QString" value="3x:0,0,0,0,0,0"/>
              <Option name="offsetFromLabelUnit" type="QString" value="MM"/>
            </Option>
          </callout>
        </settings>
      </rule>
      <rule description="zloz" scalemindenom="1000" filter="&quot;ZABIEG&quot; not in ('IA', 'IB', 'IC', 'CW', 'CP', 'CP-P', 'TW', 'TP')" scalemaxdenom="10050" key="{c1f89f7d-ccda-4e91-8fcc-6dadc8a66385}">
        <settings calloutType="simple">
          <text-style fontUnderline="0" fontWeight="50" fontSize="7" fontLetterSpacing="0" fontKerning="1" textColor="0,0,163,255" textOrientation="horizontal" namedStyle="Regular" fontStrikeout="0" fieldName="&quot;ZABIEG&quot; + '\n' + &quot;DZRB_OPS&quot;+' ['+to_string(round(&quot;POW_GRAF&quot;, 2))+' ha'+']'" useSubstitutions="0" fontItalic="0" fontSizeMapUnitScale="3x:0,0,0,0,0,0" previewBkgrdColor="0,0,0,255" fontWordSpacing="0" fontSizeUnit="Point" textOpacity="1" fontCapitals="0" fontFamily="Noto Sans" allowHtml="0" blendMode="0" multilineHeight="1" isExpression="1">
            <text-buffer bufferSizeUnits="MM" bufferBlendMode="0" bufferSize="0" bufferColor="255,255,255,255" bufferNoFill="1" bufferJoinStyle="128" bufferDraw="1" bufferOpacity="1" bufferSizeMapUnitScale="3x:0,0,0,0,0,0"/>
            <text-mask maskEnabled="0" maskType="0" maskSize="0" maskOpacity="1" maskJoinStyle="128" maskSizeUnits="MM" maskedSymbolLayers="" maskSizeMapUnitScale="3x:0,0,0,0,0,0"/>
            <background shapeSizeMapUnitScale="3x:0,0,0,0,0,0" shapeSizeX="0" shapeRadiiX="0" shapeJoinStyle="64" shapeRotation="0" shapeRadiiMapUnitScale="3x:0,0,0,0,0,0" shapeBorderWidth="0" shapeSizeType="0" shapeOffsetY="0" shapeFillColor="255,255,255,255" shapeOffsetUnit="MM" shapeBorderWidthUnit="MM" shapeBlendMode="0" shapeOffsetMapUnitScale="3x:0,0,0,0,0,0" shapeBorderColor="128,128,128,255" shapeRadiiUnit="MM" shapeRotationType="0" shapeBorderWidthMapUnitScale="3x:0,0,0,0,0,0" shapeSVGFile="" shapeOffsetX="0" shapeOpacity="1" shapeSizeY="0" shapeRadiiY="0" shapeDraw="0" shapeSizeUnit="MM" shapeType="0"/>
            <shadow shadowRadiusUnit="MM" shadowScale="100" shadowOffsetDist="1" shadowOffsetGlobal="1" shadowRadiusAlphaOnly="0" shadowUnder="0" shadowOffsetAngle="135" shadowDraw="0" shadowRadius="0" shadowOpacity="0" shadowBlendMode="6" shadowRadiusMapUnitScale="3x:0,0,0,0,0,0" shadowOffsetMapUnitScale="3x:0,0,0,0,0,0" shadowColor="0,0,0,255" shadowOffsetUnit="MM"/>
            <dd_properties>
              <Option type="Map">
                <Option name="name" type="QString" value=""/>
                <Option name="properties"/>
                <Option name="type" type="QString" value="collection"/>
              </Option>
            </dd_properties>
            <substitutions/>
          </text-style>
          <text-format wrapChar="" addDirectionSymbol="0" decimals="3" reverseDirectionSymbol="0" multilineAlign="1" useMaxLineLengthForAutoWrap="1" leftDirectionSymbol="&lt;" placeDirectionSymbol="0" formatNumbers="0" plussign="0" rightDirectionSymbol=">" autoWrapLength="0"/>
          <placement layerType="UnknownGeometry" repeatDistance="0" offsetType="0" repeatDistanceUnits="MM" fitInPolygonOnly="0" xOffset="0" dist="0" placement="0" repeatDistanceMapUnitScale="3x:0,0,0,0,0,0" geometryGenerator="" labelOffsetMapUnitScale="3x:0,0,0,0,0,0" yOffset="0" quadOffset="4" geometryGeneratorType="PointGeometry" maxCurvedCharAngleIn="25" offsetUnits="MM" polygonPlacementFlags="2" rotationAngle="0" centroidWhole="0" geometryGeneratorEnabled="0" distUnits="MM" preserveRotation="1" maxCurvedCharAngleOut="-25" predefinedPositionOrder="TR,TL,BR,BL,R,L,TSR,BSR" placementFlags="10" distMapUnitScale="3x:0,0,0,0,0,0" overrunDistanceUnit="MM" centroidInside="1" overrunDistanceMapUnitScale="3x:0,0,0,0,0,0" priority="5" overrunDistance="0"/>
          <rendering obstacle="1" fontLimitPixelSize="0" scaleMin="0" mergeLines="0" labelPerPart="0" obstacleFactor="1" scaleMax="0" maxNumLabels="2000" minFeatureSize="0" upsidedownLabels="0" displayAll="1" limitNumLabels="0" fontMinPixelSize="3" drawLabels="1" zIndex="0" scaleVisibility="0" obstacleType="1" fontMaxPixelSize="10000"/>
          <dd_properties>
            <Option type="Map">
              <Option name="name" type="QString" value=""/>
              <Option name="properties"/>
              <Option name="type" type="QString" value="collection"/>
            </Option>
          </dd_properties>
          <callout type="simple">
            <Option type="Map">
              <Option name="anchorPoint" type="QString" value="pole_of_inaccessibility"/>
              <Option name="ddProperties" type="Map">
                <Option name="name" type="QString" value=""/>
                <Option name="properties"/>
                <Option name="type" type="QString" value="collection"/>
              </Option>
              <Option name="drawToAllParts" type="bool" value="false"/>
              <Option name="enabled" type="QString" value="0"/>
              <Option name="labelAnchorPoint" type="QString" value="point_on_exterior"/>
              <Option name="lineSymbol" type="QString" value="&lt;symbol clip_to_extent=&quot;1&quot; name=&quot;symbol&quot; force_rhr=&quot;0&quot; type=&quot;line&quot; alpha=&quot;1&quot;>&lt;layer pass=&quot;0&quot; class=&quot;SimpleLine&quot; enabled=&quot;1&quot; locked=&quot;0&quot;>&lt;prop k=&quot;capstyle&quot; v=&quot;square&quot;/>&lt;prop k=&quot;customdash&quot; v=&quot;5;2&quot;/>&lt;prop k=&quot;customdash_map_unit_scale&quot; v=&quot;3x:0,0,0,0,0,0&quot;/>&lt;prop k=&quot;customdash_unit&quot; v=&quot;MM&quot;/>&lt;prop k=&quot;draw_inside_polygon&quot; v=&quot;0&quot;/>&lt;prop k=&quot;joinstyle&quot; v=&quot;bevel&quot;/>&lt;prop k=&quot;line_color&quot; v=&quot;60,60,60,255&quot;/>&lt;prop k=&quot;line_style&quot; v=&quot;solid&quot;/>&lt;prop k=&quot;line_width&quot; v=&quot;0.3&quot;/>&lt;prop k=&quot;line_width_unit&quot; v=&quot;MM&quot;/>&lt;prop k=&quot;offset&quot; v=&quot;0&quot;/>&lt;prop k=&quot;offset_map_unit_scale&quot; v=&quot;3x:0,0,0,0,0,0&quot;/>&lt;prop k=&quot;offset_unit&quot; v=&quot;MM&quot;/>&lt;prop k=&quot;ring_filter&quot; v=&quot;0&quot;/>&lt;prop k=&quot;use_custom_dash&quot; v=&quot;0&quot;/>&lt;prop k=&quot;width_map_unit_scale&quot; v=&quot;3x:0,0,0,0,0,0&quot;/>&lt;data_defined_properties>&lt;Option type=&quot;Map&quot;>&lt;Option name=&quot;name&quot; type=&quot;QString&quot; value=&quot;&quot;/>&lt;Option name=&quot;properties&quot;/>&lt;Option name=&quot;type&quot; type=&quot;QString&quot; value=&quot;collection&quot;/>&lt;/Option>&lt;/data_defined_properties>&lt;/layer>&lt;/symbol>"/>
              <Option name="minLength" type="double" value="0"/>
              <Option name="minLengthMapUnitScale" type="QString" value="3x:0,0,0,0,0,0"/>
              <Option name="minLengthUnit" type="QString" value="MM"/>
              <Option name="offsetFromAnchor" type="double" value="0"/>
              <Option name="offsetFromAnchorMapUnitScale" type="QString" value="3x:0,0,0,0,0,0"/>
              <Option name="offsetFromAnchorUnit" type="QString" value="MM"/>
              <Option name="offsetFromLabel" type="double" value="0"/>
              <Option name="offsetFromLabelMapUnitScale" type="QString" value="3x:0,0,0,0,0,0"/>
              <Option name="offsetFromLabelUnit" type="QString" value="MM"/>
            </Option>
          </callout>
        </settings>
      </rule>
    </rules>
  </labeling>
  <customproperties>
    <property key="dualview/previewExpressions" value="POZAEWID"/>
    <property key="embeddedWidgets/count" value="0"/>
    <property key="variableNames"/>
    <property key="variableValues"/>
  </customproperties>
  <blendMode>0</blendMode>
  <featureBlendMode>0</featureBlendMode>
  <layerOpacity>1</layerOpacity>
  <SingleCategoryDiagramRenderer diagramType="Histogram" attributeLegend="1">
    <DiagramCategory sizeType="MM" enabled="0" penAlpha="255" showAxis="0" scaleBasedVisibility="0" lineSizeType="MM" minimumSize="0" penWidth="0" maxScaleDenominator="1e+08" backgroundAlpha="255" spacingUnit="MM" lineSizeScale="3x:0,0,0,0,0,0" spacing="0" backgroundColor="#ffffff" height="15" opacity="1" spacingUnitScale="3x:0,0,0,0,0,0" labelPlacementMethod="XHeight" minScaleDenominator="0" width="15" scaleDependency="Area" penColor="#000000" diagramOrientation="Up" barWidth="5" rotationOffset="270" direction="1" sizeScale="3x:0,0,0,0,0,0">
      <fontProperties description="Noto Sans,11,-1,5,50,0,0,0,0,0,Regular" style="Regular"/>
      <attribute field="" label="" color="#000000"/>
      <axisSymbol>
        <symbol clip_to_extent="1" name="" force_rhr="0" type="line" alpha="1">
          <layer pass="0" class="SimpleLine" enabled="1" locked="0">
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
                <Option name="name" type="QString" value=""/>
                <Option name="properties"/>
                <Option name="type" type="QString" value="collection"/>
              </Option>
            </data_defined_properties>
          </layer>
        </symbol>
      </axisSymbol>
    </DiagramCategory>
  </SingleCategoryDiagramRenderer>
  <DiagramLayerSettings dist="0" placement="1" obstacle="0" priority="0" zIndex="0" showAll="1" linePlacementFlags="18">
    <properties>
      <Option type="Map">
        <Option name="name" type="QString" value=""/>
        <Option name="properties"/>
        <Option name="type" type="QString" value="collection"/>
      </Option>
    </properties>
  </DiagramLayerSettings>
  <geometryOptions removeDuplicateNodes="0" geometryPrecision="0">
    <activeChecks/>
    <checkConfiguration type="Map">
      <Option name="QgsGeometryGapCheck" type="Map">
        <Option name="allowedGapsBuffer" type="double" value="0"/>
        <Option name="allowedGapsEnabled" type="bool" value="false"/>
        <Option name="allowedGapsLayer" type="QString" value=""/>
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
    <default applyOnUpdate="0" field="COUNTY" expression=""/>
    <default applyOnUpdate="0" field="DISTRICT" expression=""/>
    <default applyOnUpdate="0" field="MUNICIP" expression=""/>
    <default applyOnUpdate="0" field="COMMUNITY" expression=""/>
    <default applyOnUpdate="0" field="GRP" expression=""/>
    <default applyOnUpdate="0" field="COUNTY_L" expression=""/>
    <default applyOnUpdate="0" field="ODDZ" expression=""/>
    <default applyOnUpdate="0" field="WYDZ" expression=""/>
    <default applyOnUpdate="0" field="ADR_LES" expression=""/>
    <default applyOnUpdate="0" field="POW_GRAF" expression=""/>
    <default applyOnUpdate="0" field="POZAEWID" expression=""/>
    <default applyOnUpdate="0" field="ST_ADR_LES" expression=""/>
    <default applyOnUpdate="0" field="ST_ODDZ" expression=""/>
    <default applyOnUpdate="0" field="ST_WYDZ" expression=""/>
    <default applyOnUpdate="0" field="L_EWID" expression=""/>
    <default applyOnUpdate="0" field="UDZIAL" expression=""/>
    <default applyOnUpdate="0" field="GAT" expression=""/>
    <default applyOnUpdate="0" field="WIEK" expression=""/>
    <default applyOnUpdate="0" field="ZADRZEW" expression=""/>
    <default applyOnUpdate="0" field="POW_WYDZ" expression=""/>
    <default applyOnUpdate="0" field="TYP_POW" expression=""/>
    <default applyOnUpdate="0" field="STRUKTUR" expression=""/>
    <default applyOnUpdate="0" field="SLMN_KOL" expression=""/>
    <default applyOnUpdate="0" field="STL" expression=""/>
    <default applyOnUpdate="0" field="ZABIEG" expression=""/>
    <default applyOnUpdate="0" field="POW_ZAB" expression=""/>
    <default applyOnUpdate="0" field="ODNOW" expression=""/>
    <default applyOnUpdate="0" field="POW_ODN" expression=""/>
    <default applyOnUpdate="0" field="AGROT" expression=""/>
    <default applyOnUpdate="0" field="PIEL" expression=""/>
    <default applyOnUpdate="0" field="PRZEST" expression=""/>
    <default applyOnUpdate="0" field="INNE" expression=""/>
    <default applyOnUpdate="0" field="DZ_ZRB" expression=""/>
    <default applyOnUpdate="0" field="DZRB_OPS" expression=""/>
  </defaults>
  <constraints>
    <constraint notnull_strength="0" field="COUNTY" constraints="0" unique_strength="0" exp_strength="0"/>
    <constraint notnull_strength="0" field="DISTRICT" constraints="0" unique_strength="0" exp_strength="0"/>
    <constraint notnull_strength="0" field="MUNICIP" constraints="0" unique_strength="0" exp_strength="0"/>
    <constraint notnull_strength="0" field="COMMUNITY" constraints="0" unique_strength="0" exp_strength="0"/>
    <constraint notnull_strength="0" field="GRP" constraints="0" unique_strength="0" exp_strength="0"/>
    <constraint notnull_strength="0" field="COUNTY_L" constraints="0" unique_strength="0" exp_strength="0"/>
    <constraint notnull_strength="0" field="ODDZ" constraints="0" unique_strength="0" exp_strength="0"/>
    <constraint notnull_strength="0" field="WYDZ" constraints="0" unique_strength="0" exp_strength="0"/>
    <constraint notnull_strength="0" field="ADR_LES" constraints="0" unique_strength="0" exp_strength="0"/>
    <constraint notnull_strength="0" field="POW_GRAF" constraints="0" unique_strength="0" exp_strength="0"/>
    <constraint notnull_strength="0" field="POZAEWID" constraints="0" unique_strength="0" exp_strength="0"/>
    <constraint notnull_strength="0" field="ST_ADR_LES" constraints="0" unique_strength="0" exp_strength="0"/>
    <constraint notnull_strength="0" field="ST_ODDZ" constraints="0" unique_strength="0" exp_strength="0"/>
    <constraint notnull_strength="0" field="ST_WYDZ" constraints="0" unique_strength="0" exp_strength="0"/>
    <constraint notnull_strength="0" field="L_EWID" constraints="0" unique_strength="0" exp_strength="0"/>
    <constraint notnull_strength="0" field="UDZIAL" constraints="0" unique_strength="0" exp_strength="0"/>
    <constraint notnull_strength="0" field="GAT" constraints="0" unique_strength="0" exp_strength="0"/>
    <constraint notnull_strength="0" field="WIEK" constraints="0" unique_strength="0" exp_strength="0"/>
    <constraint notnull_strength="0" field="ZADRZEW" constraints="0" unique_strength="0" exp_strength="0"/>
    <constraint notnull_strength="0" field="POW_WYDZ" constraints="0" unique_strength="0" exp_strength="0"/>
    <constraint notnull_strength="0" field="TYP_POW" constraints="0" unique_strength="0" exp_strength="0"/>
    <constraint notnull_strength="0" field="STRUKTUR" constraints="0" unique_strength="0" exp_strength="0"/>
    <constraint notnull_strength="0" field="SLMN_KOL" constraints="0" unique_strength="0" exp_strength="0"/>
    <constraint notnull_strength="0" field="STL" constraints="0" unique_strength="0" exp_strength="0"/>
    <constraint notnull_strength="0" field="ZABIEG" constraints="0" unique_strength="0" exp_strength="0"/>
    <constraint notnull_strength="0" field="POW_ZAB" constraints="0" unique_strength="0" exp_strength="0"/>
    <constraint notnull_strength="0" field="ODNOW" constraints="0" unique_strength="0" exp_strength="0"/>
    <constraint notnull_strength="0" field="POW_ODN" constraints="0" unique_strength="0" exp_strength="0"/>
    <constraint notnull_strength="0" field="AGROT" constraints="0" unique_strength="0" exp_strength="0"/>
    <constraint notnull_strength="0" field="PIEL" constraints="0" unique_strength="0" exp_strength="0"/>
    <constraint notnull_strength="0" field="PRZEST" constraints="0" unique_strength="0" exp_strength="0"/>
    <constraint notnull_strength="0" field="INNE" constraints="0" unique_strength="0" exp_strength="0"/>
    <constraint notnull_strength="0" field="DZ_ZRB" constraints="0" unique_strength="0" exp_strength="0"/>
    <constraint notnull_strength="0" field="DZRB_OPS" constraints="0" unique_strength="0" exp_strength="0"/>
  </constraints>
  <constraintExpressions>
    <constraint field="COUNTY" exp="" desc=""/>
    <constraint field="DISTRICT" exp="" desc=""/>
    <constraint field="MUNICIP" exp="" desc=""/>
    <constraint field="COMMUNITY" exp="" desc=""/>
    <constraint field="GRP" exp="" desc=""/>
    <constraint field="COUNTY_L" exp="" desc=""/>
    <constraint field="ODDZ" exp="" desc=""/>
    <constraint field="WYDZ" exp="" desc=""/>
    <constraint field="ADR_LES" exp="" desc=""/>
    <constraint field="POW_GRAF" exp="" desc=""/>
    <constraint field="POZAEWID" exp="" desc=""/>
    <constraint field="ST_ADR_LES" exp="" desc=""/>
    <constraint field="ST_ODDZ" exp="" desc=""/>
    <constraint field="ST_WYDZ" exp="" desc=""/>
    <constraint field="L_EWID" exp="" desc=""/>
    <constraint field="UDZIAL" exp="" desc=""/>
    <constraint field="GAT" exp="" desc=""/>
    <constraint field="WIEK" exp="" desc=""/>
    <constraint field="ZADRZEW" exp="" desc=""/>
    <constraint field="POW_WYDZ" exp="" desc=""/>
    <constraint field="TYP_POW" exp="" desc=""/>
    <constraint field="STRUKTUR" exp="" desc=""/>
    <constraint field="SLMN_KOL" exp="" desc=""/>
    <constraint field="STL" exp="" desc=""/>
    <constraint field="ZABIEG" exp="" desc=""/>
    <constraint field="POW_ZAB" exp="" desc=""/>
    <constraint field="ODNOW" exp="" desc=""/>
    <constraint field="POW_ODN" exp="" desc=""/>
    <constraint field="AGROT" exp="" desc=""/>
    <constraint field="PIEL" exp="" desc=""/>
    <constraint field="PRZEST" exp="" desc=""/>
    <constraint field="INNE" exp="" desc=""/>
    <constraint field="DZ_ZRB" exp="" desc=""/>
    <constraint field="DZRB_OPS" exp="" desc=""/>
  </constraintExpressions>
  <expressionfields/>
  <attributeactions>
    <defaultAction key="Canvas" value="{00000000-0000-0000-0000-000000000000}"/>
  </attributeactions>
  <attributetableconfig sortOrder="1" actionWidgetStyle="dropDown" sortExpression="&quot;POW_GRAF&quot;">
    <columns>
      <column name="COUNTY" width="-1" type="field" hidden="0"/>
      <column name="DISTRICT" width="-1" type="field" hidden="0"/>
      <column name="MUNICIP" width="-1" type="field" hidden="0"/>
      <column name="COMMUNITY" width="-1" type="field" hidden="0"/>
      <column name="GRP" width="-1" type="field" hidden="0"/>
      <column name="COUNTY_L" width="-1" type="field" hidden="0"/>
      <column name="ODDZ" width="-1" type="field" hidden="0"/>
      <column name="WYDZ" width="-1" type="field" hidden="0"/>
      <column name="ADR_LES" width="-1" type="field" hidden="0"/>
      <column name="POW_GRAF" width="-1" type="field" hidden="0"/>
      <column name="POZAEWID" width="-1" type="field" hidden="0"/>
      <column name="ST_ADR_LES" width="-1" type="field" hidden="0"/>
      <column name="ST_ODDZ" width="-1" type="field" hidden="0"/>
      <column name="ST_WYDZ" width="-1" type="field" hidden="0"/>
      <column name="L_EWID" width="-1" type="field" hidden="0"/>
      <column name="UDZIAL" width="-1" type="field" hidden="0"/>
      <column name="GAT" width="-1" type="field" hidden="0"/>
      <column name="WIEK" width="-1" type="field" hidden="0"/>
      <column name="ZADRZEW" width="-1" type="field" hidden="0"/>
      <column name="POW_WYDZ" width="-1" type="field" hidden="0"/>
      <column name="TYP_POW" width="-1" type="field" hidden="0"/>
      <column name="STRUKTUR" width="-1" type="field" hidden="0"/>
      <column name="SLMN_KOL" width="-1" type="field" hidden="0"/>
      <column name="STL" width="-1" type="field" hidden="0"/>
      <column name="ZABIEG" width="-1" type="field" hidden="0"/>
      <column name="POW_ZAB" width="-1" type="field" hidden="0"/>
      <column name="ODNOW" width="-1" type="field" hidden="0"/>
      <column name="POW_ODN" width="-1" type="field" hidden="0"/>
      <column name="AGROT" width="-1" type="field" hidden="0"/>
      <column name="PIEL" width="-1" type="field" hidden="0"/>
      <column name="PRZEST" width="-1" type="field" hidden="0"/>
      <column name="INNE" width="-1" type="field" hidden="0"/>
      <column name="DZ_ZRB" width="-1" type="field" hidden="0"/>
      <column width="-1" type="actions" hidden="1"/>
      <column name="DZRB_OPS" width="-1" type="field" hidden="0"/>
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
