using UnityEngine;

/// <summary>
/// Drives character dance animations based on alpha power tiers.
///
/// Alpha is divided into 4 tiers, each mapped to a subset of dance clips:
///   [0.0 – 0.3)  → Idle
///   [0.3 – 0.5)  → Low energy dances (Dance1, Dance2)
///   [0.5 – 0.7)  → Medium energy dances (Dance3, Dance4, Dance5)
///   [0.7 – 1.0]  → High energy dances (Dance6, Dance7)
///
/// Animations play to completion before switching. When alpha crosses
/// a tier boundary, the switch happens at the end of the current clip.
/// Within the same tier, a new random dance is picked after each clip finishes.
///
/// The Animator should have 8 states in its base layer, each playing
/// one clip with Loop Time enabled. No transitions needed.
///
/// Setup:
///   1. Attach to the character GameObject (same as Animator)
///   2. Assign the BeatSync reference
///   3. Create an Animator Controller with 8 states named:
///      Idle, Dance1, Dance2, Dance3, Dance4, Dance5, Dance6, Dance7
///   4. Add a float parameter "DanceSpeed" (default 1)
///   5. Ensure "Apply Root Motion" is OFF on the Animator component
/// </summary>
[RequireComponent(typeof(Animator))]
public class DanceAnimationController : MonoBehaviour
{
    [Header("References")]
    [SerializeField]
    [Tooltip("BeatSync component to sync animation speed with music")]
    private BeatSync beatSync;

    [Header("State Names")]
    [SerializeField]
    [Tooltip("Animator state name for idle")]
    private string idleState = "Idle";

    [SerializeField]
    [Tooltip("Animator state names for dances (7 entries, ordered by energy)")]
    private string[] danceStates = new string[]
    {
        "Dance1", "Dance2", "Dance3", "Dance4", "Dance5", "Dance6", "Dance7"
    };

    [Header("Tier Thresholds")]
    [SerializeField]
    [Tooltip("Alpha below this → Idle")]
    private float tierLowThreshold = 0.3f;

    [SerializeField]
    [Tooltip("Alpha below this (but above low) → Dance 1-2")]
    private float tierMidThreshold = 0.5f;

    [SerializeField]
    [Tooltip("Alpha below this (but above mid) → Dance 3-5")]
    private float tierHighThreshold = 0.7f;

    [Header("Transitions")]
    [SerializeField]
    [Tooltip("Crossfade duration in seconds")]
    private float crossfadeDuration = 0.8f;

    [SerializeField]
    [Tooltip("Minimum full loops of a dance before allowing a switch (even within same tier)")]
    private int minLoopsBeforeSwitch = 2;

    [Header("Speed Sync")]
    [SerializeField]
    [Tooltip("Animator float parameter for speed control")]
    private string speedParam = "DanceSpeed";

    [SerializeField]
    [Tooltip("The animation clips' natural BPM (0 = no BPM sync, use 1x speed)")]
    private float animationNaturalBPM = 0f;

    // --- Public API for AlphaAnimationDriver ---

    /// <summary>
    /// Current smoothed alpha value (0-1). Set by AlphaAnimationDriver.
    /// </summary>
    public float Alpha
    {
        get => _alpha;
        set => _alpha = Mathf.Clamp01(value);
    }

    /// <summary>Speed multiplier on top of BPM sync.</summary>
    public float SpeedMultiplier
    {
        get => _speedMultiplier;
        set => _speedMultiplier = Mathf.Max(0f, value);
    }

    private Animator _animator;
    private float _alpha;
    private float _speedMultiplier = 1f;
    private float _baseBPMSpeed = 1f;
    private int _speedHash;

    private int _currentTier = -1;
    private string _currentState;
    private int _loopCount;
    private float _lastNormalizedTime;
    private bool _pendingTierChange;
    private int _pendingTier;

    private void Awake()
    {
        _animator = GetComponent<Animator>();
        _speedHash = Animator.StringToHash(speedParam);

        // Disable root motion to prevent characters from drifting or clipping through floor
        _animator.applyRootMotion = false;
    }

    private void Start()
    {
        CalculateBaseBPMSpeed();

        _currentTier = 0;
        _currentState = idleState;
    }

    private void Update()
    {
        if (_animator == null)
            return;

        int targetTier = GetTier(_alpha);

        // Track loop completion via normalizedTime wrapping
        AnimatorStateInfo stateInfo = _animator.GetCurrentAnimatorStateInfo(0);
        float normalizedTime = stateInfo.normalizedTime % 1f;

        // Detect loop completion (normalizedTime wraps from ~1 back to ~0)
        if (normalizedTime < _lastNormalizedTime && _lastNormalizedTime > 0.5f)
        {
            _loopCount++;

            // If tier changed and we've completed enough loops, switch now
            if (_pendingTierChange && _loopCount >= minLoopsBeforeSwitch)
            {
                SwitchToTier(_pendingTier);
                _pendingTierChange = false;
            }
            // Same tier: pick a new random dance for variety
            else if (_loopCount >= minLoopsBeforeSwitch && _currentTier > 0)
            {
                string newState = PickStateForTier(_currentTier);
                if (newState != _currentState)
                {
                    _animator.CrossFadeInFixedTime(newState, crossfadeDuration);
                    _currentState = newState;
                    _loopCount = 0;
                }
            }
        }
        _lastNormalizedTime = normalizedTime;

        // Queue tier change (don't interrupt current animation)
        if (targetTier != _currentTier)
        {
            if (_currentTier == -1 || _currentTier == 0 || targetTier == 0)
            {
                // Immediate switch for idle transitions
                SwitchToTier(targetTier);
            }
            else
            {
                // Queue it — will execute when current clip finishes
                _pendingTierChange = true;
                _pendingTier = targetTier;
            }
        }

        // Update speed
        float finalSpeed = _baseBPMSpeed * _speedMultiplier;
        _animator.SetFloat(_speedHash, finalSpeed);
    }

    private void SwitchToTier(int tier)
    {
        string newState = PickStateForTier(tier);
        _animator.CrossFadeInFixedTime(newState, crossfadeDuration);
        _currentState = newState;
        _currentTier = tier;
        _loopCount = 0;
        _pendingTierChange = false;

        Debug.Log($"[DanceController] Alpha={_alpha:F2} → Tier {tier} → {newState}");
    }

    private int GetTier(float alpha)
    {
        if (alpha < tierLowThreshold) return 0;
        if (alpha < tierMidThreshold) return 1;
        if (alpha < tierHighThreshold) return 2;
        return 3;
    }

    private string PickStateForTier(int tier)
    {
        switch (tier)
        {
            case 0: return idleState;
            case 1: return danceStates[Random.Range(0, 2)];
            case 2: return danceStates[Random.Range(2, 5)];
            case 3: return danceStates[Random.Range(5, 7)];
            default: return idleState;
        }
    }

    private void CalculateBaseBPMSpeed()
    {
        if (beatSync == null || animationNaturalBPM <= 0f)
        {
            _baseBPMSpeed = 1f;
            return;
        }

        _baseBPMSpeed = beatSync.BPM / animationNaturalBPM;
        Debug.Log($"[DanceController] BPM speed: {_baseBPMSpeed:F2}x " +
                  $"(music: {beatSync.BPM}, anim: {animationNaturalBPM})");
    }
}
