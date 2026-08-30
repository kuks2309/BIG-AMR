#ifndef AMR_MOTION_CORE__ACTION_MUTEX_HPP_
#define AMR_MOTION_CORE__ACTION_MUTEX_HPP_

#include <atomic>
#include <memory>

namespace trnav_motion_core
{

/// Shared action mutual exclusion flag.
/// All action servers receive the same instance via constructor injection,
/// ensuring cross-class mutual exclusion (one action running at a time).
using ActionMutex = std::shared_ptr<std::atomic<bool>>;

/// RAII guard: atomically releases the action mutex on scope exit.
/// Place at the top of execute() to guarantee release on all exit paths.
struct ActionMutexGuard
{
    explicit ActionMutexGuard(ActionMutex m) : m_(std::move(m))
    {
    }
    ~ActionMutexGuard()
    {
        m_->store(false, std::memory_order_release);
    }

    // Non-copyable, non-movable
    ActionMutexGuard(const ActionMutexGuard &) = delete;
    ActionMutexGuard &operator=(const ActionMutexGuard &) = delete;

    ActionMutex m_;
};

} // namespace trnav_motion_core

#endif // AMR_MOTION_CORE__ACTION_MUTEX_HPP_
