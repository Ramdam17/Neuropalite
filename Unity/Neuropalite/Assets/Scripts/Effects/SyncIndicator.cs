using UnityEngine;

/// <summary>
/// Moves two indicator transforms vertically based on each participant's alpha power.
/// Y position = baseY + alpha (where alpha is 0–1).
///
/// Setup:
///   1. Attach to the "Sync" parent GameObject
///   2. Assign Left Indicator and Right Indicator transforms
/// </summary>
public class SyncIndicator : MonoBehaviour
{
    [SerializeField]
    [Tooltip("Left indicator (follows P1 alpha)")]
    private Transform leftIndicator;

    [SerializeField]
    [Tooltip("Right indicator (follows P2 alpha)")]
    private Transform rightIndicator;

    [SerializeField]
    [Tooltip("Base Y position")]
    private float baseY = 1f;

    [SerializeField]
    [Tooltip("How fast the indicator moves toward the target (higher = snappier)")]
    private float smoothSpeed = 5f;

    private void Update()
    {
        if (LSLManager.Instance == null) return;

        float alpha1 = LSLManager.Instance.GetAlpha(0);
        float alpha2 = LSLManager.Instance.GetAlpha(1);

        SmoothMoveY(leftIndicator, baseY + alpha1);
        SmoothMoveY(rightIndicator, baseY + alpha2);
    }

    private void SmoothMoveY(Transform t, float targetY)
    {
        if (t == null) return;
        var pos = t.localPosition;
        pos.y = Mathf.Lerp(pos.y, targetY, Time.deltaTime * smoothSpeed);
        t.localPosition = pos;
    }
}
