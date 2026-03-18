using UnityEngine;

/// <summary>
/// Rotates a disco ball and optionally modulates its reflections
/// based on BPM and alpha power.
///
/// Setup:
///   1. Attach to the disco ball GameObject
///   2. Optionally assign a BeatSync for beat-reactive spin speed
///   3. The material's emission can pulse on beat if configured
/// </summary>
public class DiscoBallController : MonoBehaviour
{
    [Header("Rotation")]
    [SerializeField]
    [Tooltip("Rotation speed in degrees per second")]
    private float rotationSpeed = 45f;

    [SerializeField]
    [Tooltip("Rotation axis")]
    private Vector3 rotationAxis = Vector3.up;

    [Header("Beat Reactivity")]
    [SerializeField]
    [Tooltip("BeatSync for pulse effects (optional)")]
    private BeatSync beatSync;

    [SerializeField]
    [Tooltip("Speed boost on beat (added temporarily)")]
    private float beatSpeedBoost = 90f;

    [SerializeField]
    [Tooltip("How fast the speed boost decays")]
    private float boostDecay = 5f;

    private float _currentBoost;
    private Renderer _renderer;
    private static readonly int EmissionColor = Shader.PropertyToID("_EmissionColor");

    private void Start()
    {
        _renderer = GetComponent<Renderer>();

        if (beatSync != null)
            beatSync.OnBeat += OnBeat;
    }

    private void OnDestroy()
    {
        if (beatSync != null)
            beatSync.OnBeat -= OnBeat;
    }

    private void Update()
    {
        // Decay boost
        _currentBoost = Mathf.Lerp(_currentBoost, 0f, Time.deltaTime * boostDecay);

        // Rotate
        float speed = rotationSpeed + _currentBoost;
        transform.Rotate(rotationAxis, speed * Time.deltaTime, Space.Self);
    }

    private void OnBeat(int beatNumber)
    {
        _currentBoost = beatSpeedBoost;
    }
}
