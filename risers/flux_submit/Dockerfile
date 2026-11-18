# FLUX 3 Action DROID (GD), 1 denoising step, faster timing + retry after a missed grasp (droid_retry_1step).
# Same base image and code as the 18 Nov cloud test (fretry1, 18/40).
FROM docker.io/positro/flux3-action@sha256:af8ebf7933b9cd6c15bd34d0c5a12bdfbbbd02b43f10857393b3db33ec57cccc
COPY code_flux3v3 /positronic/positronic/vendors/flux3_v3rules
ENTRYPOINT ["/bin/sh", "-c", "exec /positronic/.venv/bin/python -m positronic.vendors.flux3_v3rules.server droid_retry_1step --model.model.flux_python=/opt/flux-action/.venv/bin/python --model.model.checkpoint=\"$FLUX_POLICY_REPO\" --model.model.revision=\"$FLUX_POLICY_REVISION\" --model.model.subfolder=\"$FLUX_POLICY_SUBFOLDER\" --model.model.text_encode=cpu \"$@\"", "--"]
