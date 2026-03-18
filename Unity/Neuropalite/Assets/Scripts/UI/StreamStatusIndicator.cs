using UnityEngine;
using UnityEngine.UI;
using TMPro;
using System.Collections;

/// <summary>
/// Reusable UI widget showing the connection status of one LSL stream.
///
/// Displays a colored dot (red/amber/green) with a label and status text.
/// When in Receiving state, the dot gently pulses to convey liveness.
///
/// Setup in Unity Editor:
///   1. Create a panel with: an Image (dot), a TMP label, a TMP status text
///   2. Attach this script to the panel
///   3. Assign references in Inspector
/// </summary>
public class StreamStatusIndicator : MonoBehaviour
{
    [Header("UI References")]
    [SerializeField]
    [Tooltip("The circle/dot Image that changes color")]
    private Image dotImage;

    [SerializeField]
    [Tooltip("Label showing participant name (e.g., 'P1')")]
    private TextMeshProUGUI participantLabel;

    [SerializeField]
    [Tooltip("Text showing current status")]
    private TextMeshProUGUI statusText;

    [Header("Configuration")]
    [SerializeField]
    [Tooltip("Display name for this participant")]
    private string participantName = "P1";

    [Header("Colors")]
    [SerializeField]
    private Color disconnectedColor = new Color(1f, 0.32f, 0.32f); // #FF5252

    [SerializeField]
    private Color connectedColor = new Color(1f, 0.84f, 0f);       // #FFD600

    [SerializeField]
    private Color receivingColor = new Color(0f, 0.9f, 0.46f);     // #00E676

    [Header("Pulse Animation")]
    [SerializeField]
    [Tooltip("Pulse speed when receiving (cycles per second)")]
    private float pulseSpeed = 1.0f;

    [SerializeField]
    [Tooltip("Max scale multiplier during pulse")]
    private float pulseScale = 1.15f;

    private ConnectionState _currentState = ConnectionState.Disconnected;
    private Coroutine _pulseCoroutine;
    private Vector3 _originalDotScale;

    private void Awake()
    {
        if (dotImage != null)
            _originalDotScale = dotImage.transform.localScale;

        if (participantLabel != null)
            participantLabel.text = participantName;

        UpdateVisuals(ConnectionState.Disconnected);
    }

    /// <summary>
    /// Called each frame by StartSceneUI to update the indicator.
    /// Only triggers visual changes when state actually changes.
    /// </summary>
    public void UpdateStatus(ConnectionState newState)
    {
        if (newState == _currentState)
            return;

        _currentState = newState;
        UpdateVisuals(newState);
    }

    private void UpdateVisuals(ConnectionState state)
    {
        // Stop pulse if running
        if (_pulseCoroutine != null)
        {
            StopCoroutine(_pulseCoroutine);
            _pulseCoroutine = null;
            if (dotImage != null)
                dotImage.transform.localScale = _originalDotScale;
        }

        switch (state)
        {
            case ConnectionState.Disconnected:
                SetDot(disconnectedColor);
                SetStatusText("Disconnected");
                break;

            case ConnectionState.Connected:
                SetDot(connectedColor);
                SetStatusText("Stream found...");
                break;

            case ConnectionState.Receiving:
                SetDot(receivingColor);
                SetStatusText("Receiving");
                _pulseCoroutine = StartCoroutine(PulseAnimation());
                break;
        }
    }

    private void SetDot(Color color)
    {
        if (dotImage != null)
            dotImage.color = color;
    }

    private void SetStatusText(string text)
    {
        if (statusText != null)
            statusText.text = text;
    }

    /// <summary>
    /// Gentle breathing animation on the dot when receiving data.
    /// Uses PingPong for smooth oscillation between 1.0 and pulseScale.
    /// </summary>
    private IEnumerator PulseAnimation()
    {
        while (true)
        {
            float t = Mathf.PingPong(Time.time * pulseSpeed, 1f);
            float scale = Mathf.Lerp(1f, pulseScale, t);
            if (dotImage != null)
                dotImage.transform.localScale = _originalDotScale * scale;
            yield return null;
        }
    }
}
