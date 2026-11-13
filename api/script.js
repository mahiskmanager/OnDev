const stripe = Stripe("TU_STRIPE_PUBLIC_KEY");

document.getElementById("payBtn").addEventListener("click", async () => {
  const response = await fetch("/api/create-payment", {
    method: "POST"
  });

  const data = await response.json();

  const { error } = await stripe.confirmPayment({
    clientSecret: data.clientSecret,
    confirmParams: {
      return_url: window.location.href
    }
  });

  if (error) {
    alert(error.message);
  }
});
