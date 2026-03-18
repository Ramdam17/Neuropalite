using UnityEngine;

/// <summary>
/// Computes beat information from an AudioSource based on a known BPM.
///
/// Provides the current beat number, beat progress (0-1 within a beat),
/// and fires an event on each new beat. Other systems (lights, animation,
/// effects) subscribe to OnBeat for rhythm-synchronized behavior.
///
/// Reference:
///   BPM 125 → beat duration = 60/125 = 0.48s
///   Beat number = floor(audioTime * BPM / 60)
/// </summary>
public class BeatSync : MonoBehaviour
{
    [Header("Configuration")]
    [SerializeField]
    [Tooltip("Beats per minute of the track")]
    private float bpm = 125f;

    [SerializeField]
    [Tooltip("AudioSource to sync with")]
    private AudioSource audioSource;

    // --- Public state ---

    /// <summary>Current beat number (0-indexed, increments each beat).</summary>
    public int CurrentBeat { get; private set; }

    /// <summary>Progress within the current beat, from 0 (start) to 1 (end).</summary>
    public float BeatProgress { get; private set; }

    /// <summary>Duration of one beat in seconds.</summary>
    public float BeatDuration => 60f / bpm;

    /// <summary>The configured BPM.</summary>
    public float BPM => bpm;

    // --- Events ---

    /// <summary>Fired on each new beat. Arg: beat number.</summary>
    public System.Action<int> OnBeat;

    private int _previousBeat = -1;

    private void Update()
    {
        if (audioSource == null || !audioSource.isPlaying)
            return;

        float audioTime = audioSource.time;
        float beatFloat = audioTime * bpm / 60f;

        CurrentBeat = Mathf.FloorToInt(beatFloat);
        BeatProgress = beatFloat - CurrentBeat;

        if (CurrentBeat != _previousBeat)
        {
            _previousBeat = CurrentBeat;
            OnBeat?.Invoke(CurrentBeat);
        }
    }
}
