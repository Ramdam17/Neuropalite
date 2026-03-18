using UnityEngine;
using UnityEngine.VFX;

/// <summary>
/// Triggers VFX Graph firework effects based on alpha power dominance and synchrony.
///
/// Three firework positions:
///   - Left:   fires when P1 alpha > P2 alpha (P1 dominance)
///   - Right:  fires when P2 alpha > P1 alpha (P2 dominance)
///   - Center: fires when both alphas > 0.5 (inter-brain synchrony),
///             scales burst frequency and explosion size with synchrony strength
///
/// Controls VFX via exposed properties:
///   - "Launch delay" (float): seconds between rockets — lower = more frequent
///   - "Explosion particles" (int): particle count per explosion — higher = bigger
///
/// The VFX GameObjects stay active at all times. Play()/Stop() controls firing.
///
/// Setup:
///   1. Attach to a "Fireworks" parent GameObject
///   2. Assign 3 VisualEffect references (left, center, right)
///   3. Each VisualEffect should use a Firework VFX Graph asset from Cool Visual Effects
/// </summary>
public class FireworkController : MonoBehaviour
{
    [Header("VFX References")]
    [SerializeField]
    [Tooltip("Left firework VFX (fires when P1 > P2)")]
    private VisualEffect fireworkLeft;

    [SerializeField]
    [Tooltip("Center firework VFX (fires on synchrony)")]
    private VisualEffect fireworkCenter;

    [SerializeField]
    [Tooltip("Right firework VFX (fires when P2 > P1)")]
    private VisualEffect fireworkRight;

    [Header("Left/Right — Dominance")]
    [SerializeField]
    [Tooltip("Minimum alpha difference to trigger a side firework")]
    [Range(0f, 0.5f)]
    private float dominanceThreshold = 0.15f;

    [SerializeField]
    [Tooltip("Alpha difference at which burst rate is maximum")]
    [Range(0.1f, 1f)]
    private float maxDominanceDifference = 0.4f;

    [Header("Center — Synchrony")]
    [SerializeField]
    [Tooltip("Both alphas must exceed this to activate center firework")]
    [Range(0f, 1f)]
    private float syncMinAlpha = 0.5f;

    [SerializeField]
    [Tooltip("Maximum alpha difference considered 'in sync'")]
    [Range(0f, 0.5f)]
    private float syncMaxDifference = 0.3f;

    [SerializeField]
    [Tooltip("Both alphas above this AND close together = peak fireworks")]
    [Range(0.5f, 1f)]
    private float syncPeakAlpha = 0.8f;

    [Header("VFX — Launch Delay (seconds between rockets)")]
    [SerializeField]
    [Tooltip("Launch delay at low dominance (slow rockets)")]
    private float sideLaunchDelaySlow = 0.8f;

    [SerializeField]
    [Tooltip("Launch delay at high dominance (rapid rockets)")]
    private float sideLaunchDelayFast = 0.05f;

    [SerializeField]
    [Tooltip("Launch delay at low synchrony")]
    private float centerLaunchDelaySlow = 0.5f;

    [SerializeField]
    [Tooltip("Launch delay at peak synchrony (rapid rockets)")]
    private float centerLaunchDelayFast = 0.05f;

    [Header("Cooldown")]
    [SerializeField]
    [Tooltip("Minimum time (s) a firework stays ON before being stopped — prevents flickering")]
    private float minFireDuration = 1.5f;

    [Header("VFX — Explosion Intensity")]
    [SerializeField]
    [Tooltip("Explosion particle count at low intensity")]
    private int explosionParticlesMin = 200;

    [SerializeField]
    [Tooltip("Explosion particle count at peak intensity")]
    private int explosionParticlesMax = 1000;

    // Exposed property names in the Cool Visual Effects Firework VFX Graphs
    private const string PropLaunchDelay = "Launch delay";
    private const string PropExplosionParticles = "Explosion particles";

    private bool _leftPlaying;
    private bool _rightPlaying;
    private bool _centerPlaying;

    // Cooldown timers: track when each firework last started, to prevent rapid on/off
    private float _leftStartTime = -999f;
    private float _rightStartTime = -999f;
    private float _centerStartTime = -999f;

    private void Start()
    {
        // Stop all VFX but keep GameObjects active
        // (SetActive toggling doesn't work reliably with VFX Graph)
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
        float difference = alphaP1 - alphaP2;
        float absDifference = Mathf.Abs(difference);

        UpdateSideFirework(fireworkLeft, difference > dominanceThreshold, absDifference, ref _leftPlaying, ref _leftStartTime, "Left");
        UpdateSideFirework(fireworkRight, -difference > dominanceThreshold, absDifference, ref _rightPlaying, ref _rightStartTime, "Right");
        UpdateCenterFirework(alphaP1, alphaP2, absDifference);
    }

    private void UpdateSideFirework(VisualEffect vfx, bool shouldFire, float absDifference, ref bool isPlaying, ref float startTime, string label)
    {
        if (vfx == null) return;

        if (shouldFire)
        {
            float dominance = Mathf.InverseLerp(dominanceThreshold, maxDominanceDifference, absDifference);
            float launchDelay = Mathf.Lerp(sideLaunchDelaySlow, sideLaunchDelayFast, dominance);
            int explosionCount = (int)Mathf.Lerp(explosionParticlesMin, explosionParticlesMax, dominance);

            SetVFXProperties(vfx, launchDelay, explosionCount);

            if (!isPlaying)
            {
                vfx.Play();
                isPlaying = true;
                startTime = Time.time;
                Debug.Log($"[Fireworks] {label} PLAY — diff={absDifference:F2} delay={launchDelay:F2}s");
            }
        }
        else
        {
            // Respect minimum fire duration before stopping
            if (isPlaying && Time.time - startTime >= minFireDuration)
                StopVFX(vfx, ref isPlaying, label);
        }
    }

    private void UpdateCenterFirework(float alphaP1, float alphaP2, float absDifference)
    {
        if (fireworkCenter == null) return;

        bool bothAboveMin = alphaP1 >= syncMinAlpha && alphaP2 >= syncMinAlpha;
        bool inSync = absDifference <= syncMaxDifference;

        if (bothAboveMin && inSync)
        {
            float avgAlpha = (alphaP1 + alphaP2) * 0.5f;
            float closeness = 1f - Mathf.InverseLerp(0f, syncMaxDifference, absDifference);
            float heightScore = Mathf.InverseLerp(syncMinAlpha, syncPeakAlpha, avgAlpha);
            float synchrony = closeness * heightScore;

            float launchDelay = Mathf.Lerp(centerLaunchDelaySlow, centerLaunchDelayFast, synchrony);
            int explosionCount = (int)Mathf.Lerp(explosionParticlesMin, explosionParticlesMax, synchrony);

            SetVFXProperties(fireworkCenter, launchDelay, explosionCount);

            if (!_centerPlaying)
            {
                fireworkCenter.Play();
                _centerPlaying = true;
                _centerStartTime = Time.time;
                Debug.Log($"[Fireworks] Center PLAY — sync={synchrony:F2} delay={launchDelay:F2}s");
            }

            if (synchrony > 0.8f)
                Debug.Log($"[Fireworks] PEAK SYNCHRONY! avg={avgAlpha:F2} diff={absDifference:F2}");
        }
        else
        {
            if (_centerPlaying && Time.time - _centerStartTime >= minFireDuration)
                StopVFX(fireworkCenter, ref _centerPlaying, "Center");
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
        if (vfx == null) return;
        if (isPlaying)
        {
            vfx.Stop();
            isPlaying = false;
            Debug.Log($"[Fireworks] {label} STOP");
        }
    }

    private void StopAll()
    {
        StopVFX(fireworkLeft, ref _leftPlaying, "Left");
        StopVFX(fireworkCenter, ref _centerPlaying, "Center");
        StopVFX(fireworkRight, ref _rightPlaying, "Right");
    }
}
