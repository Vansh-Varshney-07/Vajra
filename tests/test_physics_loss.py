import torch
from vajra.downscaling.physics_loss import AtmosphericPhysicsLoss

def test_physics_loss_computation():
    loss_fn = AtmosphericPhysicsLoss(dx_meters=5000.0, dy_meters=5000.0)

    batch_size = 2
    channels = 4 # u, v, q, precip
    h, w = 32, 32

    pred = torch.randn(batch_size, channels, h, w, requires_grad=True)
    target = torch.randn(batch_size, channels, h, w)

    total_loss, metrics = loss_fn(pred, target)

    assert total_loss.item() > 0.0
    assert "divergence_penalty" in metrics
    assert "moisture_penalty" in metrics
    assert "extreme_loss" in metrics

    # Verify backpropagation works cleanly through all physics constraints
    total_loss.backward()
    assert pred.grad is not None
    assert not torch.isnan(pred.grad).any()
