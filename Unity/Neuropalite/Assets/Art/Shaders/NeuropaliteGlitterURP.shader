Shader "Custom/NeuropaliteGlitterURP"
{
    Properties
    {
        _BaseMap("Glitter Texture", 2D) = "white" {}
        _BaseColor("Base Color Tint", Color) = (1,1,1,1)
        _GlitterIntensity("Glitter Intensity", Range(0,4)) = 1.25
        _ScrollSpeed("Sparkle Scroll Speed", Range(0,2)) = 0.08
        _Threshold("Sparkle Threshold", Range(0,1)) = 0.72
        _Softness("Sparkle Softness", Range(0.001,0.25)) = 0.08
        _EmissionStrength("Emission Strength", Range(0,3)) = 0.6
    }

    SubShader
    {
        Tags
        {
            "RenderType"="Opaque"
            "Queue"="Geometry"
            "RenderPipeline"="UniversalPipeline"
        }

        Pass
        {
            Name "ForwardLit"
            Tags { "LightMode"="UniversalForward" }

            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile_fog
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

            struct Attributes
            {
                float4 positionOS : POSITION;
                float3 normalOS   : NORMAL;
                float2 uv         : TEXCOORD0;
            };

            struct Varyings
            {
                float4 positionHCS : SV_POSITION;
                float2 uv          : TEXCOORD0;
                float3 normalWS    : TEXCOORD1;
                float3 viewDirWS   : TEXCOORD2;
                float fogCoord     : TEXCOORD3;
            };

            TEXTURE2D(_BaseMap);
            SAMPLER(sampler_BaseMap);

            CBUFFER_START(UnityPerMaterial)
                float4 _BaseMap_ST;
                float4 _BaseColor;
                float _GlitterIntensity;
                float _ScrollSpeed;
                float _Threshold;
                float _Softness;
                float _EmissionStrength;
            CBUFFER_END

            Varyings vert(Attributes IN)
            {
                Varyings OUT;
                VertexPositionInputs pos = GetVertexPositionInputs(IN.positionOS.xyz);
                VertexNormalInputs nrm = GetVertexNormalInputs(IN.normalOS);

                OUT.positionHCS = pos.positionCS;
                OUT.uv = TRANSFORM_TEX(IN.uv, _BaseMap);
                OUT.normalWS = NormalizeNormalPerVertex(nrm.normalWS);
                OUT.viewDirWS = GetWorldSpaceViewDir(pos.positionWS);
                OUT.fogCoord = ComputeFogFactor(pos.positionCS.z);
                return OUT;
            }

            half4 frag(Varyings IN) : SV_Target
            {
                float2 uv1 = IN.uv + float2(_Time.y * _ScrollSpeed, _Time.y * _ScrollSpeed * 0.37);
                float2 uv2 = IN.uv * 1.73 + float2(-_Time.y * _ScrollSpeed * 0.61, _Time.y * _ScrollSpeed);

                half4 texA = SAMPLE_TEXTURE2D(_BaseMap, sampler_BaseMap, uv1);
                half4 texB = SAMPLE_TEXTURE2D(_BaseMap, sampler_BaseMap, uv2);

                half3 baseCol = texA.rgb * _BaseColor.rgb;

                // View-dependent sparkle: cheap fake spec
                half3 N = normalize(IN.normalWS);
                half3 V = normalize(IN.viewDirWS);
                half fres = pow(saturate(1.0 - dot(N, V)), 2.0);

                half sparkleSource = dot(texB.rgb, half3(0.299, 0.587, 0.114));
                half sparkleMask = smoothstep(_Threshold - _Softness, _Threshold + _Softness, sparkleSource);

                half sparkle = sparkleMask * (_GlitterIntensity + fres);
                half3 finalCol = baseCol + texB.rgb * sparkle * _EmissionStrength;

                finalCol = MixFog(finalCol, IN.fogCoord);
                return half4(finalCol, 1.0);
            }
            ENDHLSL
        }
    }
}
