<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis simplifyDrawingTol="1" simplifyDrawingHints="1" simplifyAlgorithm="0" version="3.4.0-Madeira" readOnly="0" maxScale="0" hasScaleBasedVisibilityFlag="0" simplifyMaxScale="1" styleCategories="LayerConfiguration|Symbology|Fields|Forms|AttributeTable|Rendering|CustomProperties|GeometryOptions" minScale="1e+08" simplifyLocal="1">
  <flags>
    <Identifiable>1</Identifiable>
    <Removable>1</Removable>
    <Searchable>1</Searchable>
  </flags>
  <renderer-v2 forceraster="0" symbollevels="0" enableorderby="0" type="RuleRenderer">
    <rules key="{9a02e36b-3f9e-4ea6-89a2-48f833a6ced2}">
      <rule filter=" if(right(&quot;STL&quot;, 1) = 'W' and right(&quot;STL&quot;, 2) &lt;> 'ŚW', TRUE, FALSE)" symbol="0" key="{0a590ab2-90b7-493a-b080-559708f8ba0d}" label="Wariant wilgotny"/>
      <rule filter="right(&quot;STL&quot;, 1) = 'B'" symbol="1" key="{5f3c6b84-7d18-41c9-a659-3c246c7edf91}" label="Wariant bagienny"/>
      <rule filter=" left(&quot;STL&quot;, 2) = 'BS'" symbol="2" key="{f5dfcbc8-92c1-45b4-8ec4-eb206fcd4716}" label="BS"/>
      <rule filter="left( &quot;STL&quot;, 3) = 'BŚW'" symbol="3" key="{e704a835-cc7f-419f-b060-8b1d34132a5a}" label="BŚW"/>
      <rule filter=" left(&quot;STL&quot;, 2) = 'BM'" symbol="4" key="{01d377d9-53b3-4e95-a417-71b9ffd0d91e}" label="BMŚW"/>
      <rule filter="left( &quot;STL&quot;, 4) = 'LMŚW'" symbol="5" key="{8281788f-f22b-4a0d-bdbe-76c33889dc18}" label="LMŚW"/>
      <rule filter="&quot;STL&quot; = 'LMW'" symbol="6" key="{b6dc61eb-b411-4aa8-a20d-dd5e9fd4bdc8}" label="LMw"/>
      <rule filter="&quot;STL&quot; = 'LMB'" symbol="7" key="{6e24f314-6522-4acd-a0dd-88ee55bf7563}" label="LMb"/>
      <rule filter="left( &quot;STL&quot; ,3 )= 'LŚW'" symbol="8" key="{3f448896-d32d-4dd0-a214-c521b3528e92}" label="LŚW"/>
      <rule filter="&quot;STL&quot; = 'OL'" symbol="9" key="{be5931cc-f7fd-4b28-961f-aaba05b8bb4b}" label="OL"/>
      <rule filter=" &quot;STL&quot; = 'OLJ'" symbol="10" key="{2aac6768-1025-4fe0-b74f-b970868960e1}" label="OLJ"/>
      <rule filter=" &quot;STL&quot; = 'LŁ'" symbol="11" key="{51e453e1-2fe4-4a00-97d0-87594b1958f2}" label="LŁ"/>
      <rule filter="left( &quot;STL&quot;, 5) = 'BMWYŻ'" symbol="12" key="{6a7f575e-05d8-42be-a9cf-41f42ca31ffc}" label="BMWYŻŚW"/>
      <rule filter="left( &quot;STL&quot;, 5) = 'LMWYŻ'" symbol="13" key="{53105e69-d557-4ec0-8bcc-c3dc94e67354}" label="LMWYŻŚW"/>
      <rule filter=" left(&quot;STL&quot;, 4) = 'LWYŻ'" symbol="14" key="{a0bbcdc1-effa-4ce0-a64b-ba03187f791a}" label="LWYŻŚW"/>
      <rule filter=" &quot;STL&quot; = 'LŁWYŻ'" symbol="15" key="{0ab925b1-22d9-429e-ab39-67f3e00c426a}" label="LŁWYŻ"/>
      <rule filter=" &quot;STL&quot; = 'OLJWYŻ'" symbol="16" key="{4de19924-e7e0-4ccd-be06-a3c02fd1558e}" label="OLJWYŻ"/>
      <rule filter="left( &quot;STL&quot;, 3 ) = 'BWG'" symbol="17" key="{d8fa6fbf-b51f-4f6f-b0d4-cd3141941977}" label="BWG"/>
      <rule filter="left( &quot;STL&quot;, 2) = 'BG'" symbol="18" key="{f34bec2b-c90b-49e0-bdf2-20425dd39bf3}" label="BGŚW"/>
      <rule filter="left( &quot;STL&quot;, 3) = 'BMG'" symbol="19" key="{1f7c27a1-4637-41d4-8a3b-d8985a752987}" label="BMGŚW"/>
      <rule filter="left( &quot;STL&quot;, 3) = 'LMG'" symbol="20" key="{7d7499e5-6ef9-4978-bac7-3d88ade5750b}" label="LMGŚW"/>
      <rule filter="left( &quot;STL&quot;, 2) = 'LG'" symbol="21" key="{16525c0c-a587-4602-b08b-359eebff0307}" label="LGŚW"/>
      <rule filter=" &quot;STL&quot; = 'LŁG'" symbol="22" key="{8419b150-502f-4bb8-a055-0520e87f68b6}" label="LŁG"/>
      <rule filter=" &quot;STL&quot; = 'OLJG'" symbol="23" key="{8f4367e8-6e56-4868-999a-b4f66fd88bee}" label="OLJG"/>
    </rules>
    <symbols>
      <symbol name="0" type="fill" clip_to_extent="1" alpha="1">
        <layer pass="10" class="LinePatternFill" enabled="1" locked="0">
          <prop v="0" k="angle"/>
          <prop v="147,91,219,255" k="color"/>
          <prop v="2.5" k="distance"/>
          <prop v="3x:0,0,0,0,0,0" k="distance_map_unit_scale"/>
          <prop v="MM" k="distance_unit"/>
          <prop v="0.26" k="line_width"/>
          <prop v="3x:0,0,0,0,0,0" k="line_width_map_unit_scale"/>
          <prop v="MM" k="line_width_unit"/>
          <prop v="0" k="offset"/>
          <prop v="3x:0,0,0,0,0,0" k="offset_map_unit_scale"/>
          <prop v="MM" k="offset_unit"/>
          <prop v="3x:0,0,0,0,0,0" k="outline_width_map_unit_scale"/>
          <prop v="MM" k="outline_width_unit"/>
          <data_defined_properties>
            <Option type="Map">
              <Option value="" name="name" type="QString"/>
              <Option name="properties"/>
              <Option value="collection" name="type" type="QString"/>
            </Option>
          </data_defined_properties>
          <symbol name="@0@0" type="line" clip_to_extent="1" alpha="1">
            <layer pass="0" class="SimpleLine" enabled="1" locked="0">
              <prop v="square" k="capstyle"/>
              <prop v="5;2" k="customdash"/>
              <prop v="3x:0,0,0,0,0,0" k="customdash_map_unit_scale"/>
              <prop v="MM" k="customdash_unit"/>
              <prop v="0" k="draw_inside_polygon"/>
              <prop v="bevel" k="joinstyle"/>
              <prop v="90,90,90,255" k="line_color"/>
              <prop v="solid" k="line_style"/>
              <prop v="0.35" k="line_width"/>
              <prop v="MM" k="line_width_unit"/>
              <prop v="0" k="offset"/>
              <prop v="3x:0,0,0,0,0,0" k="offset_map_unit_scale"/>
              <prop v="MM" k="offset_unit"/>
              <prop v="0" k="use_custom_dash"/>
              <prop v="3x:0,0,0,0,0,0" k="width_map_unit_scale"/>
              <data_defined_properties>
                <Option type="Map">
                  <Option value="" name="name" type="QString"/>
                  <Option name="properties"/>
                  <Option value="collection" name="type" type="QString"/>
                </Option>
              </data_defined_properties>
            </layer>
          </symbol>
        </layer>
      </symbol>
      <symbol name="1" type="fill" clip_to_extent="1" alpha="1">
        <layer pass="10" class="LinePatternFill" enabled="1" locked="0">
          <prop v="45" k="angle"/>
          <prop v="147,91,219,255" k="color"/>
          <prop v="2.5" k="distance"/>
          <prop v="3x:0,0,0,0,0,0" k="distance_map_unit_scale"/>
          <prop v="MM" k="distance_unit"/>
          <prop v="0.26" k="line_width"/>
          <prop v="3x:0,0,0,0,0,0" k="line_width_map_unit_scale"/>
          <prop v="MM" k="line_width_unit"/>
          <prop v="0" k="offset"/>
          <prop v="3x:0,0,0,0,0,0" k="offset_map_unit_scale"/>
          <prop v="MM" k="offset_unit"/>
          <prop v="3x:0,0,0,0,0,0" k="outline_width_map_unit_scale"/>
          <prop v="MM" k="outline_width_unit"/>
          <data_defined_properties>
            <Option type="Map">
              <Option value="" name="name" type="QString"/>
              <Option name="properties"/>
              <Option value="collection" name="type" type="QString"/>
            </Option>
          </data_defined_properties>
          <symbol name="@1@0" type="line" clip_to_extent="1" alpha="1">
            <layer pass="0" class="SimpleLine" enabled="1" locked="0">
              <prop v="square" k="capstyle"/>
              <prop v="5;2" k="customdash"/>
              <prop v="3x:0,0,0,0,0,0" k="customdash_map_unit_scale"/>
              <prop v="MM" k="customdash_unit"/>
              <prop v="0" k="draw_inside_polygon"/>
              <prop v="bevel" k="joinstyle"/>
              <prop v="90,90,90,255" k="line_color"/>
              <prop v="solid" k="line_style"/>
              <prop v="0.35" k="line_width"/>
              <prop v="MM" k="line_width_unit"/>
              <prop v="0" k="offset"/>
              <prop v="3x:0,0,0,0,0,0" k="offset_map_unit_scale"/>
              <prop v="MM" k="offset_unit"/>
              <prop v="0" k="use_custom_dash"/>
              <prop v="3x:0,0,0,0,0,0" k="width_map_unit_scale"/>
              <data_defined_properties>
                <Option type="Map">
                  <Option value="" name="name" type="QString"/>
                  <Option name="properties"/>
                  <Option value="collection" name="type" type="QString"/>
                </Option>
              </data_defined_properties>
            </layer>
          </symbol>
        </layer>
      </symbol>
      <symbol name="10" type="fill" clip_to_extent="1" alpha="1">
        <layer pass="0" class="SimpleFill" enabled="1" locked="0">
          <prop v="3x:0,0,0,0,0,0" k="border_width_map_unit_scale"/>
          <prop v="194,200,157,255" k="color"/>
          <prop v="bevel" k="joinstyle"/>
          <prop v="0,0" k="offset"/>
          <prop v="3x:0,0,0,0,0,0" k="offset_map_unit_scale"/>
          <prop v="MM" k="offset_unit"/>
          <prop v="0,0,0,255" k="outline_color"/>
          <prop v="solid" k="outline_style"/>
          <prop v="0.26" k="outline_width"/>
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
      <symbol name="11" type="fill" clip_to_extent="1" alpha="1">
        <layer pass="0" class="SimpleFill" enabled="1" locked="0">
          <prop v="3x:0,0,0,0,0,0" k="border_width_map_unit_scale"/>
          <prop v="200,254,206,255" k="color"/>
          <prop v="bevel" k="joinstyle"/>
          <prop v="0,0" k="offset"/>
          <prop v="3x:0,0,0,0,0,0" k="offset_map_unit_scale"/>
          <prop v="MM" k="offset_unit"/>
          <prop v="0,0,0,255" k="outline_color"/>
          <prop v="solid" k="outline_style"/>
          <prop v="0.26" k="outline_width"/>
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
      <symbol name="12" type="fill" clip_to_extent="1" alpha="1">
        <layer pass="0" class="SimpleFill" enabled="1" locked="0">
          <prop v="3x:0,0,0,0,0,0" k="border_width_map_unit_scale"/>
          <prop v="254,191,171,255" k="color"/>
          <prop v="bevel" k="joinstyle"/>
          <prop v="0,0" k="offset"/>
          <prop v="3x:0,0,0,0,0,0" k="offset_map_unit_scale"/>
          <prop v="MM" k="offset_unit"/>
          <prop v="0,0,0,255" k="outline_color"/>
          <prop v="solid" k="outline_style"/>
          <prop v="0.26" k="outline_width"/>
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
      <symbol name="13" type="fill" clip_to_extent="1" alpha="1">
        <layer pass="0" class="SimpleFill" enabled="1" locked="0">
          <prop v="3x:0,0,0,0,0,0" k="border_width_map_unit_scale"/>
          <prop v="230,193,137,255" k="color"/>
          <prop v="bevel" k="joinstyle"/>
          <prop v="0,0" k="offset"/>
          <prop v="3x:0,0,0,0,0,0" k="offset_map_unit_scale"/>
          <prop v="MM" k="offset_unit"/>
          <prop v="0,0,0,255" k="outline_color"/>
          <prop v="solid" k="outline_style"/>
          <prop v="0.26" k="outline_width"/>
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
      <symbol name="14" type="fill" clip_to_extent="1" alpha="1">
        <layer pass="0" class="SimpleFill" enabled="1" locked="0">
          <prop v="3x:0,0,0,0,0,0" k="border_width_map_unit_scale"/>
          <prop v="159,215,255,255" k="color"/>
          <prop v="bevel" k="joinstyle"/>
          <prop v="0,0" k="offset"/>
          <prop v="3x:0,0,0,0,0,0" k="offset_map_unit_scale"/>
          <prop v="MM" k="offset_unit"/>
          <prop v="0,0,0,255" k="outline_color"/>
          <prop v="solid" k="outline_style"/>
          <prop v="0.26" k="outline_width"/>
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
      <symbol name="15" type="fill" clip_to_extent="1" alpha="1">
        <layer pass="0" class="SimpleFill" enabled="1" locked="0">
          <prop v="3x:0,0,0,0,0,0" k="border_width_map_unit_scale"/>
          <prop v="152,246,206,255" k="color"/>
          <prop v="bevel" k="joinstyle"/>
          <prop v="0,0" k="offset"/>
          <prop v="3x:0,0,0,0,0,0" k="offset_map_unit_scale"/>
          <prop v="MM" k="offset_unit"/>
          <prop v="0,0,0,255" k="outline_color"/>
          <prop v="solid" k="outline_style"/>
          <prop v="0.26" k="outline_width"/>
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
      <symbol name="16" type="fill" clip_to_extent="1" alpha="1">
        <layer pass="0" class="SimpleFill" enabled="1" locked="0">
          <prop v="3x:0,0,0,0,0,0" k="border_width_map_unit_scale"/>
          <prop v="150,179,95,255" k="color"/>
          <prop v="bevel" k="joinstyle"/>
          <prop v="0,0" k="offset"/>
          <prop v="3x:0,0,0,0,0,0" k="offset_map_unit_scale"/>
          <prop v="MM" k="offset_unit"/>
          <prop v="0,0,0,255" k="outline_color"/>
          <prop v="solid" k="outline_style"/>
          <prop v="0.26" k="outline_width"/>
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
      <symbol name="17" type="fill" clip_to_extent="1" alpha="1">
        <layer pass="0" class="SimpleFill" enabled="1" locked="0">
          <prop v="3x:0,0,0,0,0,0" k="border_width_map_unit_scale"/>
          <prop v="253,212,76,255" k="color"/>
          <prop v="bevel" k="joinstyle"/>
          <prop v="0,0" k="offset"/>
          <prop v="3x:0,0,0,0,0,0" k="offset_map_unit_scale"/>
          <prop v="MM" k="offset_unit"/>
          <prop v="0,0,0,255" k="outline_color"/>
          <prop v="solid" k="outline_style"/>
          <prop v="0.26" k="outline_width"/>
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
      <symbol name="18" type="fill" clip_to_extent="1" alpha="1">
        <layer pass="0" class="SimpleFill" enabled="1" locked="0">
          <prop v="3x:0,0,0,0,0,0" k="border_width_map_unit_scale"/>
          <prop v="255,255,121,255" k="color"/>
          <prop v="bevel" k="joinstyle"/>
          <prop v="0,0" k="offset"/>
          <prop v="3x:0,0,0,0,0,0" k="offset_map_unit_scale"/>
          <prop v="MM" k="offset_unit"/>
          <prop v="0,0,0,255" k="outline_color"/>
          <prop v="solid" k="outline_style"/>
          <prop v="0.26" k="outline_width"/>
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
      <symbol name="19" type="fill" clip_to_extent="1" alpha="1">
        <layer pass="0" class="SimpleFill" enabled="1" locked="0">
          <prop v="3x:0,0,0,0,0,0" k="border_width_map_unit_scale"/>
          <prop v="254,145,145,255" k="color"/>
          <prop v="bevel" k="joinstyle"/>
          <prop v="0,0" k="offset"/>
          <prop v="3x:0,0,0,0,0,0" k="offset_map_unit_scale"/>
          <prop v="MM" k="offset_unit"/>
          <prop v="0,0,0,255" k="outline_color"/>
          <prop v="solid" k="outline_style"/>
          <prop v="0.26" k="outline_width"/>
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
      <symbol name="2" type="fill" clip_to_extent="1" alpha="1">
        <layer pass="0" class="SimpleFill" enabled="1" locked="0">
          <prop v="3x:0,0,0,0,0,0" k="border_width_map_unit_scale"/>
          <prop v="254,250,210,255" k="color"/>
          <prop v="bevel" k="joinstyle"/>
          <prop v="0,0" k="offset"/>
          <prop v="3x:0,0,0,0,0,0" k="offset_map_unit_scale"/>
          <prop v="MM" k="offset_unit"/>
          <prop v="0,0,0,255" k="outline_color"/>
          <prop v="solid" k="outline_style"/>
          <prop v="0.26" k="outline_width"/>
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
      <symbol name="20" type="fill" clip_to_extent="1" alpha="1">
        <layer pass="0" class="SimpleFill" enabled="1" locked="0">
          <prop v="3x:0,0,0,0,0,0" k="border_width_map_unit_scale"/>
          <prop v="209,168,75,255" k="color"/>
          <prop v="bevel" k="joinstyle"/>
          <prop v="0,0" k="offset"/>
          <prop v="3x:0,0,0,0,0,0" k="offset_map_unit_scale"/>
          <prop v="MM" k="offset_unit"/>
          <prop v="0,0,0,255" k="outline_color"/>
          <prop v="solid" k="outline_style"/>
          <prop v="0.26" k="outline_width"/>
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
      <symbol name="21" type="fill" clip_to_extent="1" alpha="1">
        <layer pass="0" class="SimpleFill" enabled="1" locked="0">
          <prop v="3x:0,0,0,0,0,0" k="border_width_map_unit_scale"/>
          <prop v="132,176,246,255" k="color"/>
          <prop v="bevel" k="joinstyle"/>
          <prop v="0,0" k="offset"/>
          <prop v="3x:0,0,0,0,0,0" k="offset_map_unit_scale"/>
          <prop v="MM" k="offset_unit"/>
          <prop v="0,0,0,255" k="outline_color"/>
          <prop v="solid" k="outline_style"/>
          <prop v="0.26" k="outline_width"/>
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
      <symbol name="22" type="fill" clip_to_extent="1" alpha="1">
        <layer pass="0" class="SimpleFill" enabled="1" locked="0">
          <prop v="3x:0,0,0,0,0,0" k="border_width_map_unit_scale"/>
          <prop v="135,212,186,255" k="color"/>
          <prop v="bevel" k="joinstyle"/>
          <prop v="0,0" k="offset"/>
          <prop v="3x:0,0,0,0,0,0" k="offset_map_unit_scale"/>
          <prop v="MM" k="offset_unit"/>
          <prop v="0,0,0,255" k="outline_color"/>
          <prop v="solid" k="outline_style"/>
          <prop v="0.26" k="outline_width"/>
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
      <symbol name="23" type="fill" clip_to_extent="1" alpha="1">
        <layer pass="0" class="SimpleFill" enabled="1" locked="0">
          <prop v="3x:0,0,0,0,0,0" k="border_width_map_unit_scale"/>
          <prop v="123,150,100,255" k="color"/>
          <prop v="bevel" k="joinstyle"/>
          <prop v="0,0" k="offset"/>
          <prop v="3x:0,0,0,0,0,0" k="offset_map_unit_scale"/>
          <prop v="MM" k="offset_unit"/>
          <prop v="0,0,0,255" k="outline_color"/>
          <prop v="solid" k="outline_style"/>
          <prop v="0.26" k="outline_width"/>
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
      <symbol name="3" type="fill" clip_to_extent="1" alpha="1">
        <layer pass="0" class="SimpleFill" enabled="1" locked="0">
          <prop v="3x:0,0,0,0,0,0" k="border_width_map_unit_scale"/>
          <prop v="253,251,173,255" k="color"/>
          <prop v="bevel" k="joinstyle"/>
          <prop v="0,0" k="offset"/>
          <prop v="3x:0,0,0,0,0,0" k="offset_map_unit_scale"/>
          <prop v="MM" k="offset_unit"/>
          <prop v="0,0,0,255" k="outline_color"/>
          <prop v="solid" k="outline_style"/>
          <prop v="0.26" k="outline_width"/>
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
      <symbol name="4" type="fill" clip_to_extent="1" alpha="1">
        <layer pass="0" class="SimpleFill" enabled="1" locked="0">
          <prop v="3x:0,0,0,0,0,0" k="border_width_map_unit_scale"/>
          <prop v="254,218,183,255" k="color"/>
          <prop v="bevel" k="joinstyle"/>
          <prop v="0,0" k="offset"/>
          <prop v="3x:0,0,0,0,0,0" k="offset_map_unit_scale"/>
          <prop v="MM" k="offset_unit"/>
          <prop v="0,0,0,255" k="outline_color"/>
          <prop v="solid" k="outline_style"/>
          <prop v="0.26" k="outline_width"/>
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
      <symbol name="5" type="fill" clip_to_extent="1" alpha="1">
        <layer pass="0" class="SimpleFill" enabled="1" locked="0">
          <prop v="3x:0,0,0,0,0,0" k="border_width_map_unit_scale"/>
          <prop v="230,212,181,255" k="color"/>
          <prop v="bevel" k="joinstyle"/>
          <prop v="0,0" k="offset"/>
          <prop v="3x:0,0,0,0,0,0" k="offset_map_unit_scale"/>
          <prop v="MM" k="offset_unit"/>
          <prop v="0,0,0,255" k="outline_color"/>
          <prop v="solid" k="outline_style"/>
          <prop v="0.26" k="outline_width"/>
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
      <symbol name="6" type="fill" clip_to_extent="1" alpha="1">
        <layer pass="0" class="SimpleFill" enabled="1" locked="0">
          <prop v="3x:0,0,0,0,0,0" k="border_width_map_unit_scale"/>
          <prop v="230,212,181,255" k="color"/>
          <prop v="bevel" k="joinstyle"/>
          <prop v="0,0" k="offset"/>
          <prop v="3x:0,0,0,0,0,0" k="offset_map_unit_scale"/>
          <prop v="MM" k="offset_unit"/>
          <prop v="0,0,0,255" k="outline_color"/>
          <prop v="solid" k="outline_style"/>
          <prop v="0.26" k="outline_width"/>
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
      <symbol name="7" type="fill" clip_to_extent="1" alpha="1">
        <layer pass="0" class="SimpleFill" enabled="1" locked="0">
          <prop v="3x:0,0,0,0,0,0" k="border_width_map_unit_scale"/>
          <prop v="230,212,181,255" k="color"/>
          <prop v="bevel" k="joinstyle"/>
          <prop v="0,0" k="offset"/>
          <prop v="3x:0,0,0,0,0,0" k="offset_map_unit_scale"/>
          <prop v="MM" k="offset_unit"/>
          <prop v="0,0,0,255" k="outline_color"/>
          <prop v="solid" k="outline_style"/>
          <prop v="0.26" k="outline_width"/>
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
      <symbol name="8" type="fill" clip_to_extent="1" alpha="1">
        <layer pass="0" class="SimpleFill" enabled="1" locked="0">
          <prop v="3x:0,0,0,0,0,0" k="border_width_map_unit_scale"/>
          <prop v="196,234,255,255" k="color"/>
          <prop v="bevel" k="joinstyle"/>
          <prop v="0,0" k="offset"/>
          <prop v="3x:0,0,0,0,0,0" k="offset_map_unit_scale"/>
          <prop v="MM" k="offset_unit"/>
          <prop v="0,0,0,255" k="outline_color"/>
          <prop v="solid" k="outline_style"/>
          <prop v="0.26" k="outline_width"/>
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
      <symbol name="9" type="fill" clip_to_extent="1" alpha="1">
        <layer pass="0" class="SimpleFill" enabled="1" locked="0">
          <prop v="3x:0,0,0,0,0,0" k="border_width_map_unit_scale"/>
          <prop v="171,255,126,255" k="color"/>
          <prop v="bevel" k="joinstyle"/>
          <prop v="0,0" k="offset"/>
          <prop v="3x:0,0,0,0,0,0" k="offset_map_unit_scale"/>
          <prop v="MM" k="offset_unit"/>
          <prop v="0,0,0,255" k="outline_color"/>
          <prop v="solid" k="outline_style"/>
          <prop v="0.26" k="outline_width"/>
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
  </renderer-v2>
  <customproperties>
    <property value="0" key="embeddedWidgets/count"/>
    <property value="pal" key="labeling"/>
    <property value="false" key="labeling/addDirectionSymbol"/>
    <property value="0" key="labeling/angleOffset"/>
    <property value="0" key="labeling/blendMode"/>
    <property value="0" key="labeling/bufferBlendMode"/>
    <property value="255" key="labeling/bufferColorA"/>
    <property value="255" key="labeling/bufferColorB"/>
    <property value="255" key="labeling/bufferColorG"/>
    <property value="255" key="labeling/bufferColorR"/>
    <property value="false" key="labeling/bufferDraw"/>
    <property value="128" key="labeling/bufferJoinStyle"/>
    <property value="false" key="labeling/bufferNoFill"/>
    <property value="1" key="labeling/bufferSize"/>
    <property value="false" key="labeling/bufferSizeInMapUnits"/>
    <property value="0,0,0,0,0,0" key="labeling/bufferSizeMapUnitScale"/>
    <property value="0" key="labeling/bufferTransp"/>
    <property value="false" key="labeling/centroidInside"/>
    <property value="false" key="labeling/centroidWhole"/>
    <property value="3" key="labeling/decimals"/>
    <property value="false" key="labeling/displayAll"/>
    <property value="0" key="labeling/dist"/>
    <property value="false" key="labeling/distInMapUnits"/>
    <property value="0,0,0,0,0,0" key="labeling/distMapUnitScale"/>
    <property value="false" key="labeling/drawLabels"/>
    <property value="false" key="labeling/enabled"/>
    <property value="" key="labeling/fieldName"/>
    <property value="false" key="labeling/fitInPolygonOnly"/>
    <property value="0" key="labeling/fontCapitals"/>
    <property value="MS Shell Dlg 2" key="labeling/fontFamily"/>
    <property value="false" key="labeling/fontItalic"/>
    <property value="0" key="labeling/fontLetterSpacing"/>
    <property value="false" key="labeling/fontLimitPixelSize"/>
    <property value="10000" key="labeling/fontMaxPixelSize"/>
    <property value="3" key="labeling/fontMinPixelSize"/>
    <property value="8.25" key="labeling/fontSize"/>
    <property value="false" key="labeling/fontSizeInMapUnits"/>
    <property value="0,0,0,0,0,0" key="labeling/fontSizeMapUnitScale"/>
    <property value="false" key="labeling/fontStrikeout"/>
    <property value="false" key="labeling/fontUnderline"/>
    <property value="50" key="labeling/fontWeight"/>
    <property value="0" key="labeling/fontWordSpacing"/>
    <property value="false" key="labeling/formatNumbers"/>
    <property value="true" key="labeling/isExpression"/>
    <property value="true" key="labeling/labelOffsetInMapUnits"/>
    <property value="0,0,0,0,0,0" key="labeling/labelOffsetMapUnitScale"/>
    <property value="false" key="labeling/labelPerPart"/>
    <property value="&lt;" key="labeling/leftDirectionSymbol"/>
    <property value="false" key="labeling/limitNumLabels"/>
    <property value="25" key="labeling/maxCurvedCharAngleIn"/>
    <property value="-25" key="labeling/maxCurvedCharAngleOut"/>
    <property value="2000" key="labeling/maxNumLabels"/>
    <property value="false" key="labeling/mergeLines"/>
    <property value="0" key="labeling/minFeatureSize"/>
    <property value="4294967295" key="labeling/multilineAlign"/>
    <property value="1" key="labeling/multilineHeight"/>
    <property value="Normal" key="labeling/namedStyle"/>
    <property value="true" key="labeling/obstacle"/>
    <property value="1" key="labeling/obstacleFactor"/>
    <property value="0" key="labeling/obstacleType"/>
    <property value="0" key="labeling/offsetType"/>
    <property value="0" key="labeling/placeDirectionSymbol"/>
    <property value="1" key="labeling/placement"/>
    <property value="10" key="labeling/placementFlags"/>
    <property value="false" key="labeling/plussign"/>
    <property value="TR,TL,BR,BL,R,L,TSR,BSR" key="labeling/predefinedPositionOrder"/>
    <property value="true" key="labeling/preserveRotation"/>
    <property value="#ffffff" key="labeling/previewBkgrdColor"/>
    <property value="5" key="labeling/priority"/>
    <property value="4" key="labeling/quadOffset"/>
    <property value="0" key="labeling/repeatDistance"/>
    <property value="0,0,0,0,0,0" key="labeling/repeatDistanceMapUnitScale"/>
    <property value="1" key="labeling/repeatDistanceUnit"/>
    <property value="false" key="labeling/reverseDirectionSymbol"/>
    <property value=">" key="labeling/rightDirectionSymbol"/>
    <property value="10000000" key="labeling/scaleMax"/>
    <property value="1" key="labeling/scaleMin"/>
    <property value="false" key="labeling/scaleVisibility"/>
    <property value="6" key="labeling/shadowBlendMode"/>
    <property value="0" key="labeling/shadowColorB"/>
    <property value="0" key="labeling/shadowColorG"/>
    <property value="0" key="labeling/shadowColorR"/>
    <property value="false" key="labeling/shadowDraw"/>
    <property value="135" key="labeling/shadowOffsetAngle"/>
    <property value="1" key="labeling/shadowOffsetDist"/>
    <property value="true" key="labeling/shadowOffsetGlobal"/>
    <property value="0,0,0,0,0,0" key="labeling/shadowOffsetMapUnitScale"/>
    <property value="1" key="labeling/shadowOffsetUnits"/>
    <property value="1.5" key="labeling/shadowRadius"/>
    <property value="false" key="labeling/shadowRadiusAlphaOnly"/>
    <property value="0,0,0,0,0,0" key="labeling/shadowRadiusMapUnitScale"/>
    <property value="1" key="labeling/shadowRadiusUnits"/>
    <property value="100" key="labeling/shadowScale"/>
    <property value="30" key="labeling/shadowTransparency"/>
    <property value="0" key="labeling/shadowUnder"/>
    <property value="0" key="labeling/shapeBlendMode"/>
    <property value="255" key="labeling/shapeBorderColorA"/>
    <property value="128" key="labeling/shapeBorderColorB"/>
    <property value="128" key="labeling/shapeBorderColorG"/>
    <property value="128" key="labeling/shapeBorderColorR"/>
    <property value="0" key="labeling/shapeBorderWidth"/>
    <property value="0,0,0,0,0,0" key="labeling/shapeBorderWidthMapUnitScale"/>
    <property value="1" key="labeling/shapeBorderWidthUnits"/>
    <property value="false" key="labeling/shapeDraw"/>
    <property value="255" key="labeling/shapeFillColorA"/>
    <property value="255" key="labeling/shapeFillColorB"/>
    <property value="255" key="labeling/shapeFillColorG"/>
    <property value="255" key="labeling/shapeFillColorR"/>
    <property value="64" key="labeling/shapeJoinStyle"/>
    <property value="0,0,0,0,0,0" key="labeling/shapeOffsetMapUnitScale"/>
    <property value="1" key="labeling/shapeOffsetUnits"/>
    <property value="0" key="labeling/shapeOffsetX"/>
    <property value="0" key="labeling/shapeOffsetY"/>
    <property value="0,0,0,0,0,0" key="labeling/shapeRadiiMapUnitScale"/>
    <property value="1" key="labeling/shapeRadiiUnits"/>
    <property value="0" key="labeling/shapeRadiiX"/>
    <property value="0" key="labeling/shapeRadiiY"/>
    <property value="0" key="labeling/shapeRotation"/>
    <property value="0" key="labeling/shapeRotationType"/>
    <property value="" key="labeling/shapeSVGFile"/>
    <property value="0,0,0,0,0,0" key="labeling/shapeSizeMapUnitScale"/>
    <property value="0" key="labeling/shapeSizeType"/>
    <property value="1" key="labeling/shapeSizeUnits"/>
    <property value="0" key="labeling/shapeSizeX"/>
    <property value="0" key="labeling/shapeSizeY"/>
    <property value="0" key="labeling/shapeTransparency"/>
    <property value="0" key="labeling/shapeType"/>
    <property value="&lt;substitutions/>" key="labeling/substitutions"/>
    <property value="255" key="labeling/textColorA"/>
    <property value="0" key="labeling/textColorB"/>
    <property value="0" key="labeling/textColorG"/>
    <property value="0" key="labeling/textColorR"/>
    <property value="0" key="labeling/textTransp"/>
    <property value="0" key="labeling/upsidedownLabels"/>
    <property value="false" key="labeling/useSubstitutions"/>
    <property value="" key="labeling/wrapChar"/>
    <property value="0" key="labeling/xOffset"/>
    <property value="0" key="labeling/yOffset"/>
    <property value="0" key="labeling/zIndex"/>
    <property key="variableNames"/>
    <property key="variableValues"/>
  </customproperties>
  <blendMode>0</blendMode>
  <featureBlendMode>0</featureBlendMode>
  <layerOpacity>1</layerOpacity>
  <geometryOptions removeDuplicateNodes="0" geometryPrecision="0">
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
    <field name="GRP">
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
    <field name="ODDZ">
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
    <field name="COUNTY_L">
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
    <field name="ST_WYDZ">
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
    <field name="ST_ADR_LES">
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
      <editWidget type="TextEdit">
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
      <editWidget type="TextEdit">
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
    <field name="INNE">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
  </fieldConfiguration>
  <aliases>
    <alias index="0" name="" field="COUNTY"/>
    <alias index="1" name="" field="DISTRICT"/>
    <alias index="2" name="" field="MUNICIP"/>
    <alias index="3" name="" field="COMMUNITY"/>
    <alias index="4" name="" field="GRP"/>
    <alias index="5" name="" field="WYDZ"/>
    <alias index="6" name="" field="ODDZ"/>
    <alias index="7" name="" field="ADR_LES"/>
    <alias index="8" name="" field="COUNTY_L"/>
    <alias index="9" name="" field="POW_GRAF"/>
    <alias index="10" name="" field="ST_WYDZ"/>
    <alias index="11" name="" field="ST_ODDZ"/>
    <alias index="12" name="" field="ST_ADR_LES"/>
    <alias index="13" name="" field="L_EWID"/>
    <alias index="14" name="" field="UDZIAL"/>
    <alias index="15" name="" field="GAT"/>
    <alias index="16" name="" field="WIEK"/>
    <alias index="17" name="" field="ZADRZEW"/>
    <alias index="18" name="" field="POW_WYDZ"/>
    <alias index="19" name="" field="TYP_POW"/>
    <alias index="20" name="" field="STRUKTUR"/>
    <alias index="21" name="" field="SLMN_KOL"/>
    <alias index="22" name="" field="STL"/>
    <alias index="23" name="" field="ZABIEG"/>
    <alias index="24" name="" field="POW_ZAB"/>
    <alias index="25" name="" field="ODNOW"/>
    <alias index="26" name="" field="POW_ODN"/>
    <alias index="27" name="" field="AGROT"/>
    <alias index="28" name="" field="PIEL"/>
    <alias index="29" name="" field="INNE"/>
  </aliases>
  <excludeAttributesWMS/>
  <excludeAttributesWFS/>
  <defaults>
    <default applyOnUpdate="0" expression="" field="COUNTY"/>
    <default applyOnUpdate="0" expression="" field="DISTRICT"/>
    <default applyOnUpdate="0" expression="" field="MUNICIP"/>
    <default applyOnUpdate="0" expression="" field="COMMUNITY"/>
    <default applyOnUpdate="0" expression="" field="GRP"/>
    <default applyOnUpdate="0" expression="" field="WYDZ"/>
    <default applyOnUpdate="0" expression="" field="ODDZ"/>
    <default applyOnUpdate="0" expression="" field="ADR_LES"/>
    <default applyOnUpdate="0" expression="" field="COUNTY_L"/>
    <default applyOnUpdate="0" expression="" field="POW_GRAF"/>
    <default applyOnUpdate="0" expression="" field="ST_WYDZ"/>
    <default applyOnUpdate="0" expression="" field="ST_ODDZ"/>
    <default applyOnUpdate="0" expression="" field="ST_ADR_LES"/>
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
    <default applyOnUpdate="0" expression="" field="INNE"/>
  </defaults>
  <constraints>
    <constraint constraints="0" exp_strength="0" unique_strength="0" notnull_strength="0" field="COUNTY"/>
    <constraint constraints="0" exp_strength="0" unique_strength="0" notnull_strength="0" field="DISTRICT"/>
    <constraint constraints="0" exp_strength="0" unique_strength="0" notnull_strength="0" field="MUNICIP"/>
    <constraint constraints="0" exp_strength="0" unique_strength="0" notnull_strength="0" field="COMMUNITY"/>
    <constraint constraints="0" exp_strength="0" unique_strength="0" notnull_strength="0" field="GRP"/>
    <constraint constraints="0" exp_strength="0" unique_strength="0" notnull_strength="0" field="WYDZ"/>
    <constraint constraints="0" exp_strength="0" unique_strength="0" notnull_strength="0" field="ODDZ"/>
    <constraint constraints="0" exp_strength="0" unique_strength="0" notnull_strength="0" field="ADR_LES"/>
    <constraint constraints="0" exp_strength="0" unique_strength="0" notnull_strength="0" field="COUNTY_L"/>
    <constraint constraints="0" exp_strength="0" unique_strength="0" notnull_strength="0" field="POW_GRAF"/>
    <constraint constraints="0" exp_strength="0" unique_strength="0" notnull_strength="0" field="ST_WYDZ"/>
    <constraint constraints="0" exp_strength="0" unique_strength="0" notnull_strength="0" field="ST_ODDZ"/>
    <constraint constraints="0" exp_strength="0" unique_strength="0" notnull_strength="0" field="ST_ADR_LES"/>
    <constraint constraints="0" exp_strength="0" unique_strength="0" notnull_strength="0" field="L_EWID"/>
    <constraint constraints="0" exp_strength="0" unique_strength="0" notnull_strength="0" field="UDZIAL"/>
    <constraint constraints="0" exp_strength="0" unique_strength="0" notnull_strength="0" field="GAT"/>
    <constraint constraints="0" exp_strength="0" unique_strength="0" notnull_strength="0" field="WIEK"/>
    <constraint constraints="0" exp_strength="0" unique_strength="0" notnull_strength="0" field="ZADRZEW"/>
    <constraint constraints="0" exp_strength="0" unique_strength="0" notnull_strength="0" field="POW_WYDZ"/>
    <constraint constraints="0" exp_strength="0" unique_strength="0" notnull_strength="0" field="TYP_POW"/>
    <constraint constraints="0" exp_strength="0" unique_strength="0" notnull_strength="0" field="STRUKTUR"/>
    <constraint constraints="0" exp_strength="0" unique_strength="0" notnull_strength="0" field="SLMN_KOL"/>
    <constraint constraints="0" exp_strength="0" unique_strength="0" notnull_strength="0" field="STL"/>
    <constraint constraints="0" exp_strength="0" unique_strength="0" notnull_strength="0" field="ZABIEG"/>
    <constraint constraints="0" exp_strength="0" unique_strength="0" notnull_strength="0" field="POW_ZAB"/>
    <constraint constraints="0" exp_strength="0" unique_strength="0" notnull_strength="0" field="ODNOW"/>
    <constraint constraints="0" exp_strength="0" unique_strength="0" notnull_strength="0" field="POW_ODN"/>
    <constraint constraints="0" exp_strength="0" unique_strength="0" notnull_strength="0" field="AGROT"/>
    <constraint constraints="0" exp_strength="0" unique_strength="0" notnull_strength="0" field="PIEL"/>
    <constraint constraints="0" exp_strength="0" unique_strength="0" notnull_strength="0" field="INNE"/>
  </constraints>
  <constraintExpressions>
    <constraint desc="" field="COUNTY" exp=""/>
    <constraint desc="" field="DISTRICT" exp=""/>
    <constraint desc="" field="MUNICIP" exp=""/>
    <constraint desc="" field="COMMUNITY" exp=""/>
    <constraint desc="" field="GRP" exp=""/>
    <constraint desc="" field="WYDZ" exp=""/>
    <constraint desc="" field="ODDZ" exp=""/>
    <constraint desc="" field="ADR_LES" exp=""/>
    <constraint desc="" field="COUNTY_L" exp=""/>
    <constraint desc="" field="POW_GRAF" exp=""/>
    <constraint desc="" field="ST_WYDZ" exp=""/>
    <constraint desc="" field="ST_ODDZ" exp=""/>
    <constraint desc="" field="ST_ADR_LES" exp=""/>
    <constraint desc="" field="L_EWID" exp=""/>
    <constraint desc="" field="UDZIAL" exp=""/>
    <constraint desc="" field="GAT" exp=""/>
    <constraint desc="" field="WIEK" exp=""/>
    <constraint desc="" field="ZADRZEW" exp=""/>
    <constraint desc="" field="POW_WYDZ" exp=""/>
    <constraint desc="" field="TYP_POW" exp=""/>
    <constraint desc="" field="STRUKTUR" exp=""/>
    <constraint desc="" field="SLMN_KOL" exp=""/>
    <constraint desc="" field="STL" exp=""/>
    <constraint desc="" field="ZABIEG" exp=""/>
    <constraint desc="" field="POW_ZAB" exp=""/>
    <constraint desc="" field="ODNOW" exp=""/>
    <constraint desc="" field="POW_ODN" exp=""/>
    <constraint desc="" field="AGROT" exp=""/>
    <constraint desc="" field="PIEL" exp=""/>
    <constraint desc="" field="INNE" exp=""/>
  </constraintExpressions>
  <expressionfields/>
  <attributetableconfig actionWidgetStyle="dropDown" sortExpression="&quot;STL&quot;" sortOrder="0">
    <columns>
      <column name="COUNTY" width="-1" type="field" hidden="0"/>
      <column name="DISTRICT" width="-1" type="field" hidden="0"/>
      <column name="MUNICIP" width="-1" type="field" hidden="0"/>
      <column name="COMMUNITY" width="-1" type="field" hidden="0"/>
      <column name="ODDZ" width="-1" type="field" hidden="0"/>
      <column name="WYDZ" width="-1" type="field" hidden="0"/>
      <column name="ADR_LES" width="-1" type="field" hidden="0"/>
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
      <column name="INNE" width="-1" type="field" hidden="0"/>
      <column width="-1" type="actions" hidden="1"/>
      <column name="GRP" width="-1" type="field" hidden="0"/>
      <column name="COUNTY_L" width="-1" type="field" hidden="0"/>
      <column name="POW_GRAF" width="-1" type="field" hidden="0"/>
      <column name="ST_WYDZ" width="-1" type="field" hidden="0"/>
      <column name="ST_ODDZ" width="-1" type="field" hidden="0"/>
      <column name="ST_ADR_LES" width="-1" type="field" hidden="0"/>
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
    <field editable="1" name="ADR_LES"/>
    <field editable="1" name="AGROT"/>
    <field editable="1" name="COMMUNITY"/>
    <field editable="1" name="COUNTY"/>
    <field editable="1" name="COUNTY_L"/>
    <field editable="1" name="DISTRICT"/>
    <field editable="1" name="GAT"/>
    <field editable="1" name="GRP"/>
    <field editable="1" name="INNE"/>
    <field editable="1" name="L_EWID"/>
    <field editable="1" name="MUNICIP"/>
    <field editable="1" name="ODDZ"/>
    <field editable="1" name="ODNOW"/>
    <field editable="1" name="PIEL"/>
    <field editable="1" name="POW_GRAF"/>
    <field editable="1" name="POW_ODN"/>
    <field editable="1" name="POW_WYDZ"/>
    <field editable="1" name="POW_ZAB"/>
    <field editable="1" name="SLMN_KOL"/>
    <field editable="1" name="STL"/>
    <field editable="1" name="STRUKTUR"/>
    <field editable="1" name="ST_ADR_LES"/>
    <field editable="1" name="ST_ODDZ"/>
    <field editable="1" name="ST_WYDZ"/>
    <field editable="1" name="TYP_POW"/>
    <field editable="1" name="UDZIAL"/>
    <field editable="1" name="WIEK"/>
    <field editable="1" name="WYDZ"/>
    <field editable="1" name="ZABIEG"/>
    <field editable="1" name="ZADRZEW"/>
  </editable>
  <labelOnTop>
    <field labelOnTop="0" name="ADR_LES"/>
    <field labelOnTop="0" name="AGROT"/>
    <field labelOnTop="0" name="COMMUNITY"/>
    <field labelOnTop="0" name="COUNTY"/>
    <field labelOnTop="0" name="COUNTY_L"/>
    <field labelOnTop="0" name="DISTRICT"/>
    <field labelOnTop="0" name="GAT"/>
    <field labelOnTop="0" name="GRP"/>
    <field labelOnTop="0" name="INNE"/>
    <field labelOnTop="0" name="L_EWID"/>
    <field labelOnTop="0" name="MUNICIP"/>
    <field labelOnTop="0" name="ODDZ"/>
    <field labelOnTop="0" name="ODNOW"/>
    <field labelOnTop="0" name="PIEL"/>
    <field labelOnTop="0" name="POW_GRAF"/>
    <field labelOnTop="0" name="POW_ODN"/>
    <field labelOnTop="0" name="POW_WYDZ"/>
    <field labelOnTop="0" name="POW_ZAB"/>
    <field labelOnTop="0" name="SLMN_KOL"/>
    <field labelOnTop="0" name="STL"/>
    <field labelOnTop="0" name="STRUKTUR"/>
    <field labelOnTop="0" name="ST_ADR_LES"/>
    <field labelOnTop="0" name="ST_ODDZ"/>
    <field labelOnTop="0" name="ST_WYDZ"/>
    <field labelOnTop="0" name="TYP_POW"/>
    <field labelOnTop="0" name="UDZIAL"/>
    <field labelOnTop="0" name="WIEK"/>
    <field labelOnTop="0" name="WYDZ"/>
    <field labelOnTop="0" name="ZABIEG"/>
    <field labelOnTop="0" name="ZADRZEW"/>
  </labelOnTop>
  <widgets/>
  <previewExpression>COALESCE( "L_EWID", '&lt;NULL>' )</previewExpression>
  <layerGeometryType>2</layerGeometryType>
</qgis>
