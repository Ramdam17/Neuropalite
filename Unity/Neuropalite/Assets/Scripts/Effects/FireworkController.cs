using UnityEngine;
using UnityEngine.VFX;

/// <summary>
/// Controls firework VFX visibility by moving them in/out of view.
///
/// Instead of Play()/Stop() (which have VFX Graph warm-up delays), the three
/// fireworks run continuously. Visibility is controlled by teleporting them:
///   - Visible position: near the scene
///   - Hidden position: same XY, Z = 10000 (far off screen)
///
/// Trigger conditions:
///   - Left:   P1 alpha > P2 alpha
///   - Right:  P2 alpha > P1 alpha
///   - Center: P1 alpha > syncMinAlpha AND P2 alpha > syncMinAlpha
///
/// Setup:
///   1. Attach to a "Fireworks" parent GameObject
///   2. Assign 3 VisualEffect references (left, center, right)
///   3. Each VisualEffect uses a Firework VFX Graph (Cool Visual Effects package)
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

    [Header("Visible Positions")]
    [SerializeField]
    private Vector3 leftVisiblePos = new Vector3(-15f, 0f, 20f);

    [SerializeField]
    private Vector3 rightVisiblePos = new Vector3(15f, 0f, 20f);

    [SerializeField]
    private Vector3 centerVisiblePos = new Vector3(0f, -5f, 20f);

    [Header("Center — Synchrony")]
    [SerializeField]
    [Tooltip("Both alphas must exceed this to show center firework")]
    [Range(0f, 1f)]
    private float syncMinAlpha = 0.5f;

    [Header("VFX — Intensity Scaling")]
    [SerializeField]
    [Tooltip("Launch delay when alpha difference is small")]
    private float sideLaunchDelaySlow = 0.8f;

    [SerializeField]
    [Tooltip("Launch delay when alpha difference is large")]
    private float sideLaunchDelayFast = 0.05f;

    [SerializeField]
    [Tooltip("Launch delay at low synchrony")]
    private float centerLaunchDelaySlow = 0.5f;

    [SerializeField]
    [Tooltip("Launch delay at peak synchrony")]
    private float centerLaunchDelayFast = 0.05f;

    [SerializeField]
    [Range(0.5f, 1f)]
    private float syncPeakAlpha = 0.8f;

    [SerializeField]
    private int explosionParticlesMin = 200;

    [SerializeField]
    private int explosionParticlesMax = 1000;

    private const string PropLaunchDelay = "Launch delay";
    private const string PropExplosionParticles = "Explosion particles";
    private const float HiddenZ = 10000f;

    private void Start()
    {
        // Move all off screen initially, then start them running
        HideAll();

        if (fireworkLeft != null)  fireworkLeft.Play();
        if (fireworkCenter != null) fireworkCenter.Play();
        if (fireworkRight != null) fireworkRight.Play();
    }

    private void Update()
    {
        if (LSLManager.Instance == null || !LSLManager.Instance.BothReceiving)
        {
            HideAll();
            return;
        }

        float alphaP1 = LSLManager.Instance.GetAlpha(0);
        float alphaP2 = LSLManager.Instance.GetAlpha(1);
        float absDifference = Mathf.Abs(alphaP1 - alphaP2);

        // Left/Right: strictly one or the other
        if (alphaP1 > alphaP2)
        {
            ShowSide(fireworkLeft, leftVisiblePos, absDifference, sideLaunchDelaySlow, sideLaunchDelayFast);
            Hide(fireworkRight, rightVisiblePos);
        }
        else
        {
            Hide(fireworkLeft, leftVisiblePos);
            ShowSide(fireworkRight, rightVisiblePos, absDifference, sideLaunchDelaySlow, sideLaunchDelayFast);
        }

        // Center: both above threshold
        if (alphaP1 >= syncMinAlpha && alphaP2 >= syncMinAlpha)
        {
            float avgAlpha = (alphaP1 + alphaP2) * 0.5f;
            float intensity = Mathf.InverseLerp(syncMinAlpha, syncPeakAlpha, avgAlpha);
            float launchDelay = Mathf.Lerp(centerLaunchDelaySlow, centerLaunchDelayFast, intensity);
            int explosionCount = (int)Mathf.Lerp(explosionParticlesMin, explosionParticlesMax, intensity);

            SetVFXProperties(fireworkCenter, launchDelay, explosionCount);
            SetPosition(fireworkCenter, centerVisiblePos);
        }
        else
        {
            Hide(fireworkCenter, centerVisiblePos);
        }
    }

    private void ShowSide(VisualEffect vfx, Vector3 visiblePos, float absDifference, float delaySlow, float delayFast)
    {
        if (vfx == null) return;
        float intensity = Mathf.Clamp01(absDifference);
        float launchDelay = Mathf.Lerp(delaySlow, delayFast, intensity);
        int explosionCount = (int)Mathf.Lerp(explosionParticlesMin, explosionParticlesMax, intensity);
        SetVFXProperties(vfx, launchDelay, explosionCount);
        SetPosition(vfx, visiblePos);
    }

    private void Hide(VisualEffect vfx, Vector3 visiblePos)
    {
        if (vfx == null) return;
        SetPosition(vfx, new Vector3(visiblePos.x, visiblePos.y, HiddenZ));
    }

    private void HideAll()
    {
        Hide(fireworkLeft, leftVisiblePos);
        Hide(fireworkCenter, centerVisiblePos);
        Hide(fireworkRight, rightVisiblePos);
    }

    private void SetPosition(VisualEffect vfx, Vector3 pos)
    {
        vfx.transform.position = pos;
    }

    private void SetVFXProperties(VisualEffect vfx, float launchDelay, int explosionCount)
    {
        if (vfx == null) return;
        if (vfx.HasFloat(PropLaunchDelay))
            vfx.SetFloat(PropLaunchDelay, launchDelay);
        if (vfx.HasInt(PropExplosionParticles))
            vfx.SetInt(PropExplosionParticles, explosionCount);
    }
}
