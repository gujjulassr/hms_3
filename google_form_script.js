/**
 * Google Apps Script — paste this in the Form's Script Editor.
 * Trigger: Set up an "On form submit" trigger for the onFormSubmit function.
 *
 * SETUP:
 * 1. Open your Google Form
 * 2. Click three dots → Script editor
 * 3. Paste this code
 * 4. Update API_URL to your server's public URL (use ngrok for local testing)
 * 5. Go to Triggers (clock icon) → Add trigger → onFormSubmit → On form submit
 */

const API_URL = "http://YOUR_SERVER_IP:8000/api/auth/google-form-register";
const API_KEY = "hms-register-2026";

function onFormSubmit(e) {
  try {
    const responses = e.response.getItemResponses();

    // Map form fields (adjust indices based on your form's question order)
    const data = {
      full_name: responses[0].getResponse(),        // Q1: Full Name
      email: responses[1].getResponse(),             // Q2: Email
      phone: responses[2].getResponse(),             // Q3: Phone
      preferred_date: responses[3].getResponse(),    // Q4: Preferred Date (YYYY-MM-DD)
      preferred_time: responses[4].getResponse(),    // Q5: Preferred Time (HH:MM)
      reason: responses[5].getResponse(),            // Q6: Reason for Visit
      doctor_name: responses[6].getResponse(),       // Q7: Doctor Name
      gender: responses[7] ? responses[7].getResponse() : "",           // Q8: Gender (optional)
      blood_group: responses[8] ? responses[8].getResponse() : "",      // Q9: Blood Group (optional)
      api_key: API_KEY
    };

    // Call HMS API
    const options = {
      method: "post",
      contentType: "application/json",
      payload: JSON.stringify(data),
      muteHttpExceptions: true
    };

    const response = UrlFetchApp.fetch(API_URL, options);
    const result = JSON.parse(response.getContentText());

    if (response.getResponseCode() === 200) {
      Logger.log("Success: " + result.message);

      // Optional: Send confirmation email from Apps Script too
      GmailApp.sendEmail(
        data.email,
        "Appointment Confirmed — HMS",
        "",
        {
          htmlBody: `<p>Hi ${data.full_name},</p>
            <p>Your appointment has been booked:</p>
            <ul>
              <li><b>Doctor:</b> ${result.appointment.doctor}</li>
              <li><b>Date:</b> ${result.appointment.date}</li>
              <li><b>Time:</b> ${result.appointment.time}</li>
              <li><b>UHID:</b> ${result.uhid}</li>
              <li><b>Reason:</b> ${data.reason}</li>
            </ul>
            <p>Default login password: password123</p>
            <p>— HMS Hospital Management System</p>`
        }
      );
    } else {
      Logger.log("Error: " + result.detail);
      // Notify admin of failure
      GmailApp.sendEmail(
        "admin@hms.com",
        "Form Registration Failed",
        "Patient: " + data.full_name + "\nError: " + result.detail
      );
    }
  } catch (error) {
    Logger.log("Script error: " + error.toString());
  }
}
