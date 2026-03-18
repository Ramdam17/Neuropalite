using UnityEngine;
using UnityEngine.UI;
using UnityEngine.SceneManagement;

/// <summary>
/// Controller for the StartOpalite scene.
///
/// Manages the Start button and two StreamStatusIndicator widgets.
/// Subscribes to LSLManager events for reactive status updates.
///
/// Setup in Unity Editor:
///   1. Attach to a manager GameObject in StartOpalite
///   2. Assign the Start button reference in Inspector
///   3. Assign the two StreamStatusIndicator references in Inspector
/// </summary>
public class StartSceneUI : MonoBehaviour
{
    [Header("UI References")]
    [SerializeField]
    [Tooltip("The Start button that launches RunOpalite")]
    private Button startButton;

    [SerializeField]
    [Tooltip("Status indicator for Participant 1")]
    private StreamStatusIndicator statusIndicatorP1;

    [SerializeField]
    [Tooltip("Status indicator for Participant 2")]
    private StreamStatusIndicator statusIndicatorP2;

    [Header("Scene Navigation")]
    [SerializeField]
    [Tooltip("Name of the scene to load when Start is pressed")]
    private string runSceneName = "RunOpalite";

    private void Start()
    {
        if (startButton != null)
        {
            startButton.onClick.AddListener(OnStartClicked);
        }
        else
        {
            Debug.LogWarning("[StartSceneUI] Start button not assigned in Inspector.");
        }
    }

    private void Update()
    {
        if (LSLManager.Instance == null)
            return;

        if (statusIndicatorP1 != null)
            statusIndicatorP1.UpdateStatus(LSLManager.Instance.GetState(0));

        if (statusIndicatorP2 != null)
            statusIndicatorP2.UpdateStatus(LSLManager.Instance.GetState(1));
    }

    private void OnStartClicked()
    {
        Debug.Log("[StartSceneUI] Loading RunOpalite...");

        if (SceneTransition.Instance != null)
            SceneTransition.Instance.TransitionToScene(runSceneName);
        else
            SceneManager.LoadScene(runSceneName);
    }
}
