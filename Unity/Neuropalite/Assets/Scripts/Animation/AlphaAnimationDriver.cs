using UnityEngine;

/// <summary>
/// Reads LSL alpha power values and feeds them to DanceAnimationController.
///
/// Applies exponential moving average smoothing to avoid jerky transitions
/// between animation tiers. The smoothed alpha is passed directly to the
/// DanceAnimationController which handles tier selection and animation switching.
///
/// Reference:
///   Alpha power (8-12 Hz) typically increases during relaxed states
///   and decreases during active engagement. Higher alpha = more energetic dance.
///
/// Setup:
///   1. Attach to each character GameObject
///   2. Set participantIndex (0 or 1)
///   3. Assign the DanceAnimationController reference
/// </summary>
public class AlphaAnimationDriver : MonoBehaviour
{
    [Header("Configuration")]
    [SerializeField]
    [Tooltip("Which participant's alpha to use (0 or 1)")]
    private int participantIndex = 0;

    [Header("References")]
    [SerializeField]
    [Tooltip("The dance controller to drive")]
    private DanceAnimationController danceController;

    [SerializeField]
    [Tooltip("SkinnedMeshRenderer with facial blendshapes")]
    private SkinnedMeshRenderer faceMesh;

    [Header("Smoothing")]
    [SerializeField]
    [Tooltip("Smoothing factor (0 = no smoothing, 0.99 = very smooth). " +
             "Controls how quickly the animation responds to alpha changes.")]
    [Range(0f, 0.99f)]
    private float smoothingFactor = 0.9f;

    [Header("Facial Blendshapes")]
    [SerializeField]
    [Tooltip("Blendshape index for sad face")]
    private int sadBlendshapeIndex = 11;

    [SerializeField]
    [Tooltip("Blendshape index for happy face")]
    private int happyBlendshapeIndex = 14;

    [Header("Fallback")]
    [SerializeField]
    [Tooltip("Alpha value to use when LSL data is not available")]
    private float fallbackAlpha = 0.5f;

    private float _smoothedAlpha;
    private bool _initialized;

    private void Update()
    {
        if (LSLManager.Instance == null || danceController == null)
            return;

        float rawAlpha;

        if (LSLManager.Instance.GetState(participantIndex) == ConnectionState.Receiving)
        {
            rawAlpha = LSLManager.Instance.GetAlpha(participantIndex);

            // Exponential moving average for smooth transitions
            if (!_initialized)
            {
                _smoothedAlpha = rawAlpha;
                _initialized = true;
            }
            else
            {
                _smoothedAlpha = smoothingFactor * _smoothedAlpha + (1f - smoothingFactor) * rawAlpha;
            }
        }
        else
        {
            // No LSL data — drift toward fallback
            _smoothedAlpha = Mathf.Lerp(_smoothedAlpha, fallbackAlpha, Time.deltaTime * 2f);
        }

        // Feed smoothed alpha directly to the dance controller
        danceController.Alpha = _smoothedAlpha;

        // Drive facial blendshapes from inter-brain sync (shared across both characters)
        float sync = LSLManager.Instance != null ? LSLManager.Instance.Sync : 0f;
        UpdateFacialExpression(sync);
    }

    /// <summary>
    /// Maps inter-brain sync to facial blendshapes:
    ///   [0.0 – 0.3] → Sad face: 100 → 0 (linear ramp down)
    ///   [0.3 – 0.8] → Happy face: 0 → 100 (linear ramp up)
    /// Both characters share the same sync value, so they smile together.
    /// </summary>
    private void UpdateFacialExpression(float sync)
    {
        if (faceMesh == null) return;

        float sadWeight = 0f;
        float happyWeight = 0f;

        if (sync < 0.3f)
        {
            // Sync 0→0.3 maps to sad 100→0
            sadWeight = (1f - sync / 0.3f) * 100f;
        }
        else
        {
            // Sync 0.3→0.8 maps to happy 0→100
            happyWeight = Mathf.Clamp01((sync - 0.3f) / 0.5f) * 100f;
        }

        faceMesh.SetBlendShapeWeight(sadBlendshapeIndex, sadWeight);
        faceMesh.SetBlendShapeWeight(happyBlendshapeIndex, happyWeight);
    }
}
