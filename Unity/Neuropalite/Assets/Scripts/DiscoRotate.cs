using UnityEngine;

public class DiscoRotate : MonoBehaviour
{

    float angle = 0 ;
    // Start is called once before the first execution of Update after the MonoBehaviour is created
    void Start()
    {
        
    }

    void Update()
    {
        angle += 4 * Mathf.PI * Time.deltaTime;
        // Rotate around world Y axis (up) regardless of model's local orientation
        transform.rotation = Quaternion.Euler(0f, angle, 0f);
    }
}
