using UnityEngine;
using UnityEngine.UI;

/// <summary>
/// Displays a "HIGH FIVE" friendship bracelet image when both
/// participants' alpha power is synchronized (both above threshold).
///
/// The bracelet fades in smoothly when synchrony is detected and
/// fades out when synchrony is lost. Uses a world-space Canvas
/// so the bracelet appears as a 3D element in the scene.
///
/// Reference:
///   Inter-brain synchrony feedback reinforces social bonding.
///   Dumas et al. (2010). Inter-Brain Synchronization during Social Interaction.
///   PLoS ONE, 5(8), e12166.
///
/// Setup:
///   1. Attach to a GameObject positioned between the two characters
///   2. Assign the friendship bracelet sprite (friendship.png)
///   3. Configure the alpha threshold for synchrony detection
///   4. Optionally assign a BeatSync for pulse-on-beat effect
/// </summary>
public class SyncFeedback : MonoBehaviour
{
    [Header("Bracelet Image")]
    [SerializeField]
    [Tooltip("The friendship bracelet sprite to display")]
    private Sprite braceletSprite;

    [SerializeField]
    [Tooltip("Size of the bracelet display in world units")]
    private Vector2 displaySize = new Vector2(2f, 0.6f);

    [Header("Synchrony Detection")]
    [SerializeField]
    [Tooltip("Both alphas must exceed this value to show the bracelet")]
    [Range(0f, 1f)]
    private float syncThreshold = 0.6f;

    [SerializeField]
    [Tooltip("Both alphas must stay above threshold for this many seconds")]
    private float sustainDuration = 1.5f;

    [SerializeField]
    [Tooltip("Bracelet stays visible for at least this many seconds after trigger")]
    private float minDisplayDuration = 3f;

    [Header("Animation")]
    [SerializeField]
    [Tooltip("Fade in speed")]
    private float fadeInSpeed = 2f;

    [SerializeField]
    [Tooltip("Fade out speed")]
    private float fadeOutSpeed = 1f;

    [SerializeField]
    [Tooltip("Gentle floating amplitude (world units)")]
    private float floatAmplitude = 0.1f;

    [SerializeField]
    [Tooltip("Floating speed")]
    private float floatSpeed = 1.5f;

    [Header("Beat Reactivity (Optional)")]
    [SerializeField]
    [Tooltip("BeatSync for scale pulse on beat")]
    private BeatSync beatSync;

    [SerializeField]
    [Tooltip("Scale pulse amount on beat")]
    private float beatPulseScale = 0.05f;

    private CanvasGroup _canvasGroup;
    private RectTransform _imageRect;
    private float _sustainTimer;
    private float _displayTimer;
    private bool _showing;
    private float _targetAlpha;
    private Vector3 _basePosition;
    private float _beatPulse;

    private void Start()
    {
        _basePosition = transform.position;
        CreateWorldSpaceUI();

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
        UpdateSynchronyDetection();
        UpdateVisuals();
    }

    private void UpdateSynchronyDetection()
    {
        if (LSLManager.Instance == null || !LSLManager.Instance.BothReceiving)
        {
            _sustainTimer = 0f;
            if (!_showing)
                _targetAlpha = 0f;
            return;
        }

        float alphaP1 = LSLManager.Instance.GetAlpha(0);
        float alphaP2 = LSLManager.Instance.GetAlpha(1);
        bool bothAbove = alphaP1 >= syncThreshold && alphaP2 >= syncThreshold;

        if (bothAbove)
        {
            _sustainTimer += Time.deltaTime;

            if (_sustainTimer >= sustainDuration && !_showing)
            {
                _showing = true;
                _targetAlpha = 1f;
                _displayTimer = 0f;
                Debug.Log("[SyncFeedback] Synchrony detected! Showing HIGH FIVE bracelet.");
            }
        }
        else
        {
            _sustainTimer = 0f;
        }

        // Track display time
        if (_showing)
        {
            _displayTimer += Time.deltaTime;

            // Only allow fade out after minimum display and when sync is lost
            if (!bothAbove && _displayTimer >= minDisplayDuration)
            {
                _showing = false;
                _targetAlpha = 0f;
            }
        }
    }

    private void UpdateVisuals()
    {
        if (_canvasGroup == null)
            return;

        // Smooth fade
        float fadeSpeed = _targetAlpha > _canvasGroup.alpha ? fadeInSpeed : fadeOutSpeed;
        _canvasGroup.alpha = Mathf.MoveTowards(_canvasGroup.alpha, _targetAlpha, Time.deltaTime * fadeSpeed);

        // Gentle floating motion
        if (_canvasGroup.alpha > 0.01f)
        {
            float yOffset = Mathf.Sin(Time.time * floatSpeed) * floatAmplitude;
            transform.position = _basePosition + Vector3.up * yOffset;
        }

        // Beat pulse decay
        _beatPulse = Mathf.Lerp(_beatPulse, 0f, Time.deltaTime * 8f);
        if (_imageRect != null)
        {
            float scale = 1f + _beatPulse * beatPulseScale;
            _imageRect.localScale = Vector3.one * scale;
        }
    }

    private void OnBeat(int beatNumber)
    {
        if (_showing)
            _beatPulse = 1f;
    }

    private void CreateWorldSpaceUI()
    {
        // World-space canvas so the bracelet exists in 3D space
        var canvas = gameObject.AddComponent<Canvas>();
        canvas.renderMode = RenderMode.WorldSpace;

        var canvasRect = GetComponent<RectTransform>();
        canvasRect.sizeDelta = displaySize;

        _canvasGroup = gameObject.AddComponent<CanvasGroup>();
        _canvasGroup.alpha = 0f;
        _canvasGroup.interactable = false;
        _canvasGroup.blocksRaycasts = false;

        // Bracelet image
        var imageObj = new GameObject("BraceletImage");
        imageObj.transform.SetParent(transform, false);

        var image = imageObj.AddComponent<Image>();
        image.sprite = braceletSprite;
        image.preserveAspect = true;
        image.raycastTarget = false;

        _imageRect = image.rectTransform;
        _imageRect.anchorMin = Vector2.zero;
        _imageRect.anchorMax = Vector2.one;
        _imageRect.offsetMin = Vector2.zero;
        _imageRect.offsetMax = Vector2.zero;
    }
}
