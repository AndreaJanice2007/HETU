const ART = {
  patient: { src: "/login-patient.png?v=2", title: "Patient" },
  doctor: { src: "/login-doctor.png?v=2", title: "Doctor" },
  surrogate: { src: "/login-surrogate.png?v=2", title: "Surrogate" },
};

export default function LoginRoleArt({ role }) {
  const art = ART[role] || ART.patient;
  return (
    <img
      src={art.src}
      alt=""
      className="h-auto w-full max-h-[min(62vh,34rem)] object-contain object-center"
      aria-hidden
    />
  );
}
