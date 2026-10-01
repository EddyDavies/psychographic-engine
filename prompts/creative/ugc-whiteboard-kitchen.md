# Format: UGC Whiteboard Kitchen

> Low-res UGC-style photo of a person holding a whiteboard with handwritten text in a lived-in kitchen.

## Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `reference_images` | Product photos to place in scene | `products/images/starter-kit/` |
| `whiteboard_text` | Handwritten text on the whiteboard | "My mirrors have never been this clear!" |
| `subject_description` | Who is holding the board | "A happy British man in his late 40s, wearing a polo" |

## Prompt

[CAMERA]: An unedited, low-resolution vertical photo from a 2018 smartphone. Visible digital noise/grain in the shadows. Slight wide-angle lens distortion. The image is a bit "flat" with no professional color grading.
[SUBJECT]: A happy British man in his late 40s, posing to smile at the camera, as if his friend is taking the photo. He is wearing a polo. His posture is slightly slumped and natural. His face is fully visible with no shadows.
[ACTION/POSING]: He is holding a whiteboard with both hands, gripping the sides clumsily. On the board, "{whiteboard_text}" is written in messy, uneven black permanent marker. The board is fully visible with nothing in front of it, and is partially cutting off his shoulder.
[THE PRODUCTS]: Show all the products in the reference image. They are placed in front so they are all visible but not perfectly centered.
[THE ENVIRONMENT]: A cute quaint lived-in British kitchen during the daytime. The lighting is from sunlight from a window making the scene bright overall. The background is "busy" with authentic details: a white toaster with a stray cord, a drying rack with a few mismatched mugs, a white radiator, and a light switch on the wall.
[STYLE]: A "cute" photo sent in a family group chat. No symmetry, no "AI glow," no dramatic lighting. Just a raw, candid home moment.

### [LEARNINGS]

- Whiteboard text renders reliably when kept under 8 words
- The "low-resolution smartphone" instruction is critical — without it, AI produces polished studio-quality images
- Kitchen details (toaster, drying rack, radiator) ground the scene in reality
- Subject description should specify nationality/age/clothing for consistency
