/// <summary>
/// Data model for LSL stream connection state.
/// Used by LSLManager to track each participant's stream.
/// </summary>
public enum ConnectionState
{
    /// <summary>Stream not found on the network.</summary>
    Disconnected,

    /// <summary>Stream resolved but no data received recently.</summary>
    Connected,

    /// <summary>Stream resolved and data actively flowing.</summary>
    Receiving
}
