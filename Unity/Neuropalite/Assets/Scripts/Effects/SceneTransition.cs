using System.Collections;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.UI;

/// <summary>
/// Manages fade-in/fade-out transitions between scenes.
///
/// Creates a persistent full-screen overlay that fades to black before
/// a scene load and fades from black after the new scene is ready.
///
/// Uses DontDestroyOnLoad so the overlay persists across scene changes.
///
/// Setup:
///   1. Attach to an empty GameObject in StartOpalite
///   2. It will auto-create a Canvas with a black Image overlay
///   3. Call TransitionToScene() instead of SceneManager.LoadScene()
/// </summary>
public class SceneTransition : MonoBehaviour
{
    [Header("Transition Settings")]
    [SerializeField]
    [Tooltip("Duration of fade out (seconds)")]
    private float fadeOutDuration = 0.8f;

    [SerializeField]
    [Tooltip("Duration of fade in (seconds)")]
    private float fadeInDuration = 0.8f;

    [SerializeField]
    [Tooltip("Color of the fade overlay")]
    private Color fadeColor = Color.black;

    public static SceneTransition Instance { get; private set; }

    private CanvasGroup _canvasGroup;
    private bool _isTransitioning;

    private void Awake()
    {
        if (Instance != null && Instance != this)
        {
            Destroy(gameObject);
            return;
        }

        Instance = this;
        DontDestroyOnLoad(gameObject);
        CreateOverlay();

        // Fade in on first scene
        _canvasGroup.alpha = 1f;
        StartCoroutine(FadeIn());
    }

    private void OnEnable()
    {
        SceneManager.sceneLoaded += OnSceneLoaded;
    }

    private void OnDisable()
    {
        SceneManager.sceneLoaded -= OnSceneLoaded;
    }

    private void OnSceneLoaded(Scene scene, LoadSceneMode mode)
    {
        if (_canvasGroup != null && _canvasGroup.alpha > 0f)
        {
            StartCoroutine(FadeIn());
        }
    }

    /// <summary>
    /// Transition to a scene with fade out → load → fade in.
    /// Call this instead of SceneManager.LoadScene().
    /// </summary>
    public void TransitionToScene(string sceneName)
    {
        if (_isTransitioning)
            return;

        StartCoroutine(DoTransition(sceneName));
    }

    private IEnumerator DoTransition(string sceneName)
    {
        _isTransitioning = true;

        // Fade out
        yield return StartCoroutine(FadeOut());

        // Load scene
        SceneManager.LoadScene(sceneName);

        // FadeIn will be triggered by OnSceneLoaded
        _isTransitioning = false;
    }

    private IEnumerator FadeOut()
    {
        float elapsed = 0f;
        _canvasGroup.alpha = 0f;
        _canvasGroup.blocksRaycasts = true;

        while (elapsed < fadeOutDuration)
        {
            elapsed += Time.deltaTime;
            _canvasGroup.alpha = Mathf.Clamp01(elapsed / fadeOutDuration);
            yield return null;
        }

        _canvasGroup.alpha = 1f;
    }

    private IEnumerator FadeIn()
    {
        float elapsed = 0f;
        _canvasGroup.alpha = 1f;

        while (elapsed < fadeInDuration)
        {
            elapsed += Time.deltaTime;
            _canvasGroup.alpha = 1f - Mathf.Clamp01(elapsed / fadeInDuration);
            yield return null;
        }

        _canvasGroup.alpha = 0f;
        _canvasGroup.blocksRaycasts = false;
    }

    private void CreateOverlay()
    {
        // Create a canvas that renders on top of everything
        var canvas = gameObject.AddComponent<Canvas>();
        canvas.renderMode = RenderMode.ScreenSpaceOverlay;
        canvas.sortingOrder = 999;

        // CanvasGroup for alpha control
        _canvasGroup = gameObject.AddComponent<CanvasGroup>();
        _canvasGroup.alpha = 0f;
        _canvasGroup.blocksRaycasts = false;

        // Full-screen image
        var imageObj = new GameObject("FadeOverlay");
        imageObj.transform.SetParent(transform, false);

        var image = imageObj.AddComponent<Image>();
        image.color = fadeColor;
        image.raycastTarget = true;

        // Stretch to fill screen
        var rect = image.rectTransform;
        rect.anchorMin = Vector2.zero;
        rect.anchorMax = Vector2.one;
        rect.offsetMin = Vector2.zero;
        rect.offsetMax = Vector2.zero;
    }
}
