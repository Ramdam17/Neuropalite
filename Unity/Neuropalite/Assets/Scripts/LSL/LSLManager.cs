using UnityEngine;

/// <summary>
/// Singleton service managing LSL stream connections for both participants.
///
/// Persists across scenes (DontDestroyOnLoad) so that streams remain
/// connected during scene transitions (StartOpalite → RunOpalite → back).
///
/// Usage:
///   - Access via LSLManager.Instance
///   - Subscribe to OnStatusChanged / OnAlphaUpdated for reactive updates
///   - Read GetState(index) / GetAlpha(index) for polling
///
/// Setup in Unity Editor:
///   1. Create empty GameObject "LSLManager" in StartOpalite scene
///   2. Attach this script
///   3. Two AlphaPowerReceiver children are created automatically
///      (or you can add them manually and assign via Inspector)
/// </summary>
public class LSLManager : MonoBehaviour
{
    // --- Singleton ---
    public static LSLManager Instance { get; private set; }

    [Header("Stream Names")]
    [SerializeField]
    [Tooltip("LSL stream name for Participant 1")]
    private string streamNameP1 = "AlphaPower_P1";

    [SerializeField]
    [Tooltip("LSL stream name for Participant 2")]
    private string streamNameP2 = "AlphaPower_P2";

    // --- Events ---
    /// <summary>
    /// Fired when a participant's connection state changes.
    /// Args: (participant index 0 or 1, new state)
    /// </summary>
    public System.Action<int, ConnectionState> OnStatusChanged;

    /// <summary>
    /// Fired when a new alpha value is received.
    /// Args: (participant index 0 or 1, alpha value)
    /// </summary>
    public System.Action<int, float> OnAlphaUpdated;

    // --- Sync metric ---
    /// <summary>
    /// Continuous inter-brain synchrony metric in [0, 1].
    /// Computed as 1 - |alphaP1 - alphaP2|, smoothed with EMA.
    /// 1.0 = perfect sync, 0.0 = maximum divergence.
    /// </summary>
    public float Sync { get; private set; }

    [Header("Sync")]
    [SerializeField]
    [Tooltip("EMA smoothing for sync metric (0 = instant, 0.99 = very smooth)")]
    [Range(0f, 0.99f)]
    private float syncSmoothing = 0.85f;

    // --- Internal ---
    private AlphaPowerReceiver[] _receivers = new AlphaPowerReceiver[2];

    private void Awake()
    {
        if (Instance != null && Instance != this)
        {
            Destroy(gameObject);
            return;
        }

        Instance = this;
        DontDestroyOnLoad(gameObject);

        SetupReceivers();
    }

    private void Update()
    {
        if (BothReceiving)
        {
            float rawSync = 1f - Mathf.Abs(GetAlpha(0) - GetAlpha(1));
            Sync = syncSmoothing * Sync + (1f - syncSmoothing) * rawSync;
        }
        else
        {
            // No shared data — drift sync toward 0
            Sync = Mathf.Lerp(Sync, 0f, Time.deltaTime * 2f);
        }
    }

    /// <summary>
    /// Get the connection state for a participant.
    /// </summary>
    /// <param name="participantIndex">0 or 1</param>
    public ConnectionState GetState(int participantIndex)
    {
        ValidateIndex(participantIndex);
        return _receivers[participantIndex].State;
    }

    /// <summary>
    /// Get the latest alpha power value for a participant.
    /// </summary>
    /// <param name="participantIndex">0 or 1</param>
    public float GetAlpha(int participantIndex)
    {
        ValidateIndex(participantIndex);
        return _receivers[participantIndex].LatestAlphaValue;
    }

    /// <summary>
    /// Get the receiver component for a participant (for direct access).
    /// </summary>
    /// <param name="participantIndex">0 or 1</param>
    public AlphaPowerReceiver GetReceiver(int participantIndex)
    {
        ValidateIndex(participantIndex);
        return _receivers[participantIndex];
    }

    /// <summary>
    /// Check if both participants are actively receiving data.
    /// </summary>
    public bool BothReceiving =>
        _receivers[0].State == ConnectionState.Receiving &&
        _receivers[1].State == ConnectionState.Receiving;

    private void SetupReceivers()
    {
        string[] names = { streamNameP1, streamNameP2 };

        for (int i = 0; i < 2; i++)
        {
            // Check if a receiver child already exists
            if (transform.childCount > i)
            {
                var existing = transform.GetChild(i).GetComponent<AlphaPowerReceiver>();
                if (existing != null)
                {
                    _receivers[i] = existing;
                    SubscribeToReceiver(i);
                    continue;
                }
            }

            // Create receiver as child GameObject
            var receiverGO = new GameObject($"AlphaPowerReceiver_P{i + 1}");
            receiverGO.transform.SetParent(transform);

            var receiver = receiverGO.AddComponent<AlphaPowerReceiver>();
            receiver.Initialize(names[i]);

            _receivers[i] = receiver;
            SubscribeToReceiver(i);

            Debug.Log($"[LSLManager] Created receiver for '{names[i]}'");
        }
    }

    private void SubscribeToReceiver(int index)
    {
        int capturedIndex = index; // capture for closure

        _receivers[index].OnStateChanged += (state) =>
        {
            OnStatusChanged?.Invoke(capturedIndex, state);
        };

        _receivers[index].OnAlphaReceived += (alpha) =>
        {
            OnAlphaUpdated?.Invoke(capturedIndex, alpha);
        };
    }

    private void ValidateIndex(int index)
    {
        if (index < 0 || index > 1)
        {
            Debug.LogError($"[LSLManager] Invalid participant index: {index}. Must be 0 or 1.");
        }
    }
}
