# HTML Formatting Rules

When writing or modifying HTML files, adhere strictly to the following formatting standards:

1. **Single-Line Text Content for Inline / Typography Tags**:
   - The text content inside `<p>`, `<h1>`~`<h6>`, `<li>`, `<a>`, `<span>`, `<td>`, `<th>`, `<dt>`, `<dd>`, and similar tags MUST remain on a single line (no artificial line breaks or hard wraps within sentences).
   - Never split a sentence across multiple lines inside these tags.

2. **Formatting Example**:
   - **Correct**:
     ```html
     <div class="frame mb-3">
         <p>Welcome to your value investing starting point! We break down value investing into easy, step-by-step lessons you can learn on a coffee break.</p>
     </div>
     ```
   - **Incorrect**:
     ```html
     <div class="frame mb-3">
         <p>Welcome to your value investing starting point! We break down value investing into easy,
             step-by-step lessons you can learn on a coffee break.</p>
     </div>
     ```
