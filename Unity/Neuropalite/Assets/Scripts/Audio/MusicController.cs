using UnityEngine;
using UnityEngine.SceneManagement;

/// <summary>
/// Controls music playback in the RunOpalite scene.
///
/// Starts playing the track on scene load, monitors playback,
/// and returns to StartOpalite when the track ends.
///
/// Setup in Unity Editor:
///   1. Create a GameObject "MusicController" in RunOpalite
///   2. Add an AudioSource component (don't enable Play On Awake — this script handles it)
///   3. Assign the AudioClip (Opalite.mp3) to the AudioSource
///   4. Attach this script
///   5. Assign the AudioSource reference
///   6. Optionally attach a BeatSync component to the same GameObject
/// </summary>
public class MusicController : MonoBehaviour
{
    [Header("References")]
    [SerializeField]
    [Tooltip("AudioSource with the music clip assigned")]
    private AudioSource audioSource;

    [Header("Scene Navigation")]
    [SerializeField]
    [Tooltip("Scene to return to when music ends")]
    private string returnSceneName = "StartOpalite";

    [Header("Debug")]
    [SerializeField]
    [Tooltip("Log beat info periodically")]
    private bool logBeats = false;

    /// <summary>True while music is playing.</summary>
    public bool IsPlaying => audioSource != null && audioSource.isPlaying;

    /// <summary>Current playback time in seconds.</summary>
    public float PlaybackTime => audioSource != null ? audioSource.time : 0f;

    /// <summary>Total duration of the track in seconds.</summary>
    public float TrackDuration => audioSource != null && audioSource.clip != null
        ? audioSource.clip.length : 0f;

    /// <summary>Playback progress from 0 to 1.</summary>
    public float Progress => TrackDuration > 0 ? PlaybackTime / TrackDuration : 0f;

    private BeatSync _beatSync;
    private bool _hasStartedPlaying;

    private void Start()
    {
        if (audioSource == null)
        {
            Debug.LogError("[MusicController] AudioSource not assigned!");
            return;
        }

        // Ensure Play On Awake is off — we control playback
        audioSource.playOnAwake = false;
        audioSource.loop = false;

        // Get BeatSync if on same GameObject
        _beatSync = GetComponent<BeatSync>();

        if (logBeats && _beatSync != null)
        {
            _beatSync.OnBeat += (beat) =>
            {
                if (beat % 4 == 0) // Log every 4 beats (= 1 bar)
                    Debug.Log($"[MusicController] Bar {beat / 4 + 1} (beat {beat})");
            };
        }

        // Start playing
        audioSource.Play();
        _hasStartedPlaying = true;
        Debug.Log($"[MusicController] Playing '{audioSource.clip.name}' ({TrackDuration:F1}s)");
    }

    private void Update()
    {
        if (!_hasStartedPlaying || audioSource == null)
            return;

        // Detect end of track
        if (!audioSource.isPlaying)
        {
            Debug.Log("[MusicController] Track ended. Returning to StartOpalite.");

            if (SceneTransition.Instance != null)
                SceneTransition.Instance.TransitionToScene(returnSceneName);
            else
                SceneManager.LoadScene(returnSceneName);
        }
    }
}
