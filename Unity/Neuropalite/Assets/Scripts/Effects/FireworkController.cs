using UnityEngine;
using UnityEngine.VFX;

/// <summary>
/// Triggers VFX Graph firework effects based on alpha power values:
///   - Left:   fires when P1 alpha > P2 alpha
///   - Right:  fires when P2 alpha > P1 alpha
///   - Center: fires when both alphas > 0.5
///
/// Left and right are mutually exclusive (only the dominant side fires).
/// Intensity scales with the magnitude of the alpha difference.
///
/// Controls VFX via exposed properties:
///   - "Launch delay" (float): seconds between rockets — lower = more frequent
///   - "Explosion particles" (int): particle count per explosion — higher = bigger
///
/// Setup:
///   1. Attach to a "Fireworks" parent GameObject
///   2. Assign 3 VisualEffect references (left, center, right)
///   3. Each VisualEffect should use a Firework VFX Graph (Cool Visual Effects package)
/// </summary>
public class FireworkController : MonoBehaviour
{
    [Header("VFX References")]
    [SerializeField]
    [Tooltip("Left firework VFX (fires when P1 > P2)")]
    private VisualEffect fireworkLeft;

    [SerializeField]
    [Tooltip("Center firework VFX (fires when both > syncMinAlpha)")]
    private VisualEffect fireworkCenter;

    [SerializeField]
    [Tooltip("Right firework VFX (fires when P2 > P1)")]
    private VisualEffect fireworkRight;

    [Header("Center — Synchrony")]
    [SerializeField]
    [Tooltip("Both alphas must exceed this to activate center firework")]
    [Range(0f, 1f)]
    private float syncMinAlpha = 0.5f;

    [SerializeField]
    [Tooltip("Both alphas above this = peak center fireworks")]
    [Range(0.5f, 1f)]
    private float syncPeakAlpha = 0.8f;

    [Header("VFX — Launch Delay (seconds between rockets)")]
    [SerializeField]
    [Tooltip("Launch delay when alpha difference is small (slow rockets)")]
    private float sideLaunchDelaySlow = 0.8f;

    [SerializeField]
    [Tooltip("Launch delay when alpha difference is large (rapid rockets)")]
    private float sideLaunchDelayFast = 0.05f;

    [SerializeField]
    [Tooltip("Launch delay at low synchrony")]
    private float centerLaunchDelaySlow = 0.5f;

    [SerializeField]
    [Tooltip("Launch delay at peak synchrony")]
    private float centerLaunchDelayFast = 0.05f;

    [Header("VFX — Explosion Intensity")]
    [SerializeField]
    [Tooltip("Explosion particle count at low intensity")]
    private int explosionParticlesMin = 200;

    [SerializeField]
    [Tooltip("Explosion particle count at peak intensity")]
    private int explosionParticlesMax = 1000;

    [Header("Cooldown")]
    [SerializeField]
    [Tooltip("Minimum time (s) a firework stays ON before being stopped — prevents flickering")]
    private float minFireDuration = 1.5f;

    // Exposed property names in the Cool Visual Effects Firework VFX Graphs
    private const string PropLaunchDelay = "Launch delay";
    private const string PropExplosionParticles = "Explosion particles";

    private bool _leftPlaying;
    private bool _rightPlaying;
    private bool _centerPlaying;

    private float _leftStartTime = -999f;
    private float _rightStartTime = -999f;
    private float _centerStartTime = -999f;

    private void Start()
    {
        StopVFX(fireworkLeft, ref _leftPlaying, "Left");
        StopVFX(fireworkCenter, ref _centerPlaying, "Center");
        StopVFX(fireworkRight, ref _rightPlaying, "Right");
    }

    private void Update()
    {
        if (LSLManager.Instance == null || !LSLManager.Instance.BothReceiving)
        {
            StopAll();
            return;
        }

        float alphaP1 = LSLManager.Instance.GetAlpha(0);
        float alphaP2 = LSLManager.Instance.GetAlpha(1);
        float difference = alphaP1 - alphaP2; // positive = P1 leads, negative = P2 leads
        float absDifference = Mathf.Abs(difference);

        // Left/Right: strictly one or the other based on which alpha is higher
        if (alphaP1 > alphaP2)
        {
            StopVFX(fireworkRight, ref _rightPlaying, "Right");
            PlaySideFirework(fireworkLeft, absDifference, ref _leftPlaying, ref _leftStartTime, "Left");
        }
        else
        {
            StopVFX(fireworkLeft, ref _leftPlaying, "Left");
            PlaySideFirework(fireworkRight, absDifference, ref _rightPlaying, ref _rightStartTime, "Right");
        }

        // Center: both above threshold, independent of left/right
        bool bothAbove = alphaP1 >= syncMinAlpha && alphaP2 >= syncMinAlpha;
        if (bothAbove)
        {
            float avgAlpha = (alphaP1 + alphaP2) * 0.5f;
            float intensity = Mathf.InverseLerp(syncMinAlpha, syncPeakAlpha, avgAlpha);
            float launchDelay = Mathf.Lerp(centerLaunchDelaySlow, centerLaunchDelayFast, intensity);
            int explosionCount = (int)Mathf.Lerp(explosionParticlesMin, explosionParticlesMax, intensity);

            SetVFXProperties(fireworkCenter, launchDelay, explosionCount);

            if (!_centerPlaying)
            {
                fireworkCenter.Play();
                _centerPlaying = true;
                _centerStartTime = Time.time;
                Debug.Log($"[Fireworks] Center PLAY — avg={avgAlpha:F2} delay={launchDelay:F2}s");
            }
        }
        else if (_centerPlaying && Time.time - _centerStartTime >= minFireDuration)
        {
            StopVFX(fireworkCenter, ref _centerPlaying, "Center");
        }
    }

    private void PlaySideFirework(VisualEffect vfx, float absDifference, ref bool isPlaying, ref float startTime, string label)
    {
        if (vfx == null) return;

        // Intensity scales with how different the alphas are (0 = barely different, 1 = max apart)
        float intensity = Mathf.Clamp01(absDifference);
        float launchDelay = Mathf.Lerp(sideLaunchDelaySlow, sideLaunchDelayFast, intensity);
        int explosionCount = (int)Mathf.Lerp(explosionParticlesMin, explosionParticlesMax, intensity);

        SetVFXProperties(vfx, launchDelay, explosionCount);

        if (!isPlaying)
        {
            vfx.Play();
            isPlaying = true;
            startTime = Time.time;
            Debug.Log($"[Fireworks] {label} PLAY — diff={absDifference:F2} delay={launchDelay:F2}s");
        }
    }

    private void SetVFXProperties(VisualEffect vfx, float launchDelay, int explosionCount)
    {
        if (vfx.HasFloat(PropLaunchDelay))
            vfx.SetFloat(PropLaunchDelay, launchDelay);

        if (vfx.HasInt(PropExplosionParticles))
            vfx.SetInt(PropExplosionParticles, explosionCount);
    }

    private void StopVFX(VisualEffect vfx, ref bool isPlaying, string label)
    {
        if (vfx == null || !isPlaying) return;
        vfx.Stop();
        isPlaying = false;
        Debug.Log($"[Fireworks] {label} STOP");
    }

    private void StopAll()
    {
        StopVFX(fireworkLeft, ref _leftPlaying, "Left");
        StopVFX(fireworkCenter, ref _centerPlaying, "Center");
        StopVFX(fireworkRight, ref _rightPlaying, "Right");
    }
}
