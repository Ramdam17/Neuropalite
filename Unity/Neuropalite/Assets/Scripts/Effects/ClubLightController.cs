using UnityEngine;

/// <summary>
/// Controls SpaceZeta spotlight models for a nightclub effect.
///
/// Automatically creates a Unity Spot Light inside each spotlight model
/// so that real light is projected onto the floor and reflects off objects.
/// Also animates the emission color of the spotlight meshes.
///
/// Setup:
///   1. Attach to the parent "Lights" GameObject containing Spotlight children
///   2. Assign the BeatSync reference
///   3. Children should be SpaceZeta Spotlight prefab instances
/// </summary>
public class ClubLightController : MonoBehaviour
{
    [Header("References")]
    [SerializeField]
    [Tooltip("BeatSync to synchronize light changes")]
    private BeatSync beatSync;

    [Header("Color Cycling")]
    [SerializeField]
    [Tooltip("Colors to cycle through on each beat")]
    private Color[] beatColors = new Color[]
    {
        new Color(1f, 0.2f, 0.6f),    // Hot pink
        new Color(0.2f, 0.8f, 1f),    // Cyan
        new Color(1f, 0.84f, 0f),     // Gold
        new Color(0.6f, 0.2f, 1f),    // Purple
        new Color(0f, 1f, 0.6f),      // Mint
        new Color(1f, 0.4f, 0.2f),    // Coral
    };

    [SerializeField]
    [Tooltip("Change color every N beats")]
    private int beatsPerColorChange = 2;

    [Header("Spot Lights (auto-created)")]
    [SerializeField]
    [Tooltip("Range of the projected spot lights")]
    private float spotRange = 15f;

    [SerializeField]
    [Tooltip("Spot angle in degrees")]
    private float spotAngle = 40f;

    [SerializeField]
    [Tooltip("Base spot light intensity")]
    private float spotIntensity = 20f;

    [SerializeField]
    [Tooltip("Inner spot angle ratio (0-1, controls falloff softness)")]
    [Range(0f, 1f)]
    private float innerSpotRatio = 0.4f;

    [Header("Emission")]
    [SerializeField]
    [Tooltip("Base emission intensity (HDR multiplier)")]
    private float baseEmissionIntensity = 2f;

    [SerializeField]
    [Tooltip("Peak emission on beat (multiplier of base)")]
    private float pulseMultiplier = 3f;

    [SerializeField]
    [Tooltip("How fast the pulse decays")]
    private float pulseDecay = 8f;

    [Header("Rotation")]
    [SerializeField]
    [Tooltip("Enable spotlight rotation")]
    private bool enableRotation = true;

    [SerializeField]
    [Tooltip("Base rotation speed (each spot gets a unique variation)")]
    private float rotationSpeed = 25f;

    [SerializeField]
    [Tooltip("Maximum tilt angle from pointing down toward the stage (degrees)")]
    private float rotationRange = 35f;

    private Renderer[] _renderers;
    private Light[] _spotLights;
    private MaterialPropertyBlock[] _propBlocks;
    private Quaternion[] _baseRotations;
    private Transform[] _spotlightTransforms;
    private Color[] _spotColors;
    private float _pulseValue;

    private static readonly int EmissionColor = Shader.PropertyToID("_EmissionColor");

    private void Start()
    {
        // Collect direct children FIRST (the SpaceZeta spotlight models)
        // before we add projected lights as additional children
        int childCount = transform.childCount;
        _spotlightTransforms = new Transform[childCount];
        _baseRotations = new Quaternion[childCount];
        _spotLights = new Light[childCount];

        for (int i = 0; i < childCount; i++)
        {
            _spotlightTransforms[i] = transform.GetChild(i);
            _baseRotations[i] = _spotlightTransforms[i].localRotation;
        }

        // Now create projected lights (added as siblings, after the models)
        for (int i = 0; i < childCount; i++)
        {
            _spotLights[i] = CreateSpotLight(_spotlightTransforms[i], i);
        }

        // Find all renderers for emission control
        _renderers = GetComponentsInChildren<Renderer>();
        _propBlocks = new MaterialPropertyBlock[_renderers.Length];
        for (int i = 0; i < _renderers.Length; i++)
            _propBlocks[i] = new MaterialPropertyBlock();

        // Assign a fixed color to each spotlight from the palette
        _spotColors = new Color[childCount];
        for (int i = 0; i < childCount; i++)
        {
            _spotColors[i] = beatColors[i % beatColors.Length];
            if (_spotLights[i] != null)
                _spotLights[i].color = _spotColors[i];
        }

        if (beatSync != null)
            beatSync.OnBeat += OnBeat;

        Debug.Log($"[ClubLightController] Created {childCount} spot lights, " +
                  $"found {_renderers.Length} renderers to animate");
    }

    private Light CreateSpotLight(Transform parent, int index)
    {
        // Create as sibling (child of "Lights" parent), NOT child of SpaceZeta model
        // This avoids local-axis confusion with the model's orientation
        var lightObj = new GameObject($"ProjectedLight_{index}");
        lightObj.transform.SetParent(transform, false);

        // Same world position as the spotlight model
        lightObj.transform.position = parent.position;

        var light = lightObj.AddComponent<Light>();
        light.type = LightType.Spot;
        light.range = spotRange;
        light.spotAngle = spotAngle;
        light.innerSpotAngle = spotAngle * innerSpotRatio;
        light.intensity = spotIntensity;
        light.shadows = LightShadows.None;
        light.renderMode = LightRenderMode.ForcePixel;

        return light;
    }

    private void OnDestroy()
    {
        if (beatSync != null)
            beatSync.OnBeat -= OnBeat;
    }

    private void Update()
    {
        // Decay pulse
        _pulseValue = Mathf.Lerp(_pulseValue, 0f, Time.deltaTime * pulseDecay);

        float emissionIntensity = baseEmissionIntensity * (1f + _pulseValue * (pulseMultiplier - 1f));
        float lightIntensity = spotIntensity * (1f + _pulseValue * (pulseMultiplier - 1f));

        // Update emission on renderers
        for (int i = 0; i < _renderers.Length; i++)
        {
            int spotIndex = Mathf.Min(i * _spotLights.Length / Mathf.Max(1, _renderers.Length), _spotLights.Length - 1);
            Color emissionHDR = _spotColors[spotIndex] * emissionIntensity;

            _renderers[i].GetPropertyBlock(_propBlocks[i]);
            _propBlocks[i].SetColor(EmissionColor, emissionHDR);
            _renderers[i].SetPropertyBlock(_propBlocks[i]);
        }

        // Rotate spotlight models AND projected lights
        for (int i = 0; i < _spotlightTransforms.Length; i++)
        {
            float speedVariation = 0.5f + (float)i / _spotlightTransforms.Length * 1f;
            float direction = (i % 2 == 0) ? 1f : -1f;
            float speed = rotationSpeed * speedVariation * direction;

            float sweepAngle = Time.time * speed
                + (float)i / _spotlightTransforms.Length * 360f;

            // Rotate SpaceZeta model
            if (enableRotation)
            {
                _spotlightTransforms[i].localRotation = _baseRotations[i]
                    * Quaternion.AngleAxis(sweepAngle, Vector3.up)
                    * Quaternion.Euler(rotationRange, 0f, 0f);
            }

            // Rotate projected light independently in world space:
            // point mostly down (90°) minus tilt, then sweep around Y
            if (_spotLights[i] != null)
            {
                _spotLights[i].intensity = lightIntensity;
                _spotLights[i].transform.rotation =
                    Quaternion.AngleAxis(sweepAngle, Vector3.up)
                    * Quaternion.Euler(90f - rotationRange, 0f, 0f);
            }
        }
    }

    private void OnBeat(int beatNumber)
    {
        _pulseValue = 1f;
    }

    /// <summary>
    /// Modulate spot light intensity based on alpha power.
    /// </summary>
    public void SetAlphaModulation(float normalizedAlpha)
    {
        spotIntensity = Mathf.Lerp(1f, 5f, normalizedAlpha);
    }
}
