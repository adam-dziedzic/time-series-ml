import sys
import torch.nn as nn
import torch.nn.functional as F
import torch
from cnns.nnlib.robustness.batch_attack.attack import attack_cw
from cnns.nnlib.utils.object import Object
from cnns.foolbox.foolbox_3_0_0 import foolbox
from cleverhans.future.torch.attacks.spsa import spsa
import numpy as np


class Attack(object):

    def __init__(self, dataloader, criterion=None, gpu_id=0,
                 epsilon=0.031, attack_method='pgd',
                 iterations=7, eot=1):

        if criterion is not None:
            self.criterion = criterion
        else:
            self.criterion = nn.CrossEntropyLoss()

        self.dataloader = dataloader
        self.epsilon = epsilon
        self.gpu_id = gpu_id  # this is integer
        self.iterations = iterations
        if eot is None or eot == 0:
            # compute the gradient at least once
            self.eot = 1
        else:
            self.eot = eot

        if attack_method == 'fgsm':
            self.attack_method = self.fgsm
        elif attack_method == 'pgd':
            self.attack_method = self.pgd
        elif attack_method == 'cw':
            self.attack_method = self.cw
        elif attack_method == 'boundary':
            self.attack_method = self.boundary_attack

    def update_params(self, epsilon=None, dataloader=None, attack_method=None):
        if epsilon is not None:
            self.epsilon = epsilon
        if dataloader is not None:
            self.dataloader = dataloader

        if attack_method is not None:
            if attack_method == 'fgsm':
                self.attack_method = self.fgsm
            elif attack_method == 'pgd':
                self.attack_method = self.pgd

    def fgsm(self, model, data, target, data_min=0, data_max=1):

        model.eval()
        # perturbed_data = copy.deepcopy(data)
        perturbed_data = data.clone()

        perturbed_data.requires_grad = True
        output = model(perturbed_data)
        loss = F.cross_entropy(output, target)

        if perturbed_data.grad is not None:
            perturbed_data.grad.data.zero_()

        loss.backward()

        # Collect the element-wise sign of the data gradient
        sign_data_grad = perturbed_data.grad.data.sign()
        perturbed_data.requires_grad = False

        with torch.no_grad():
            # Create the perturbed image by adjusting each pixel of the input image
            perturbed_data += self.epsilon * sign_data_grad
            # Adding clipping to maintain [min,max] range, default 0,1 for image
            perturbed_data.clamp_(data_min, data_max)

        return perturbed_data

    def pgd(self, model, data, target, k=None, a=0.01, random_start=True,
            d_min=0, d_max=1, eot=None):
        """

        :param model: the model to attack
        :param data: clean input data
        :param target: the target class for the clean data
        :param k: number of iterations of the attack
        :param a: the scaling of the gradients used by the attack
        :param random_start: should we start from random perturbation of the clean data
        :param d_min: data min value
        :param d_max: data max value
        :param eot: number of iterations for EOT
        :return: adversarially perturbed data
        """
        if k is None:
            k = self.iterations

        if eot is None:
            eot = self.eot
        elif eot == 0:
            # compute the gradient at least once
            eot = 1

        model.eval()
        perturbed_data = data.clone()

        perturbed_data.requires_grad = True

        data_max = data + self.epsilon
        data_min = data - self.epsilon
        data_max.clamp_(d_min, d_max)
        data_min.clamp_(d_min, d_max)

        if random_start:
            with torch.no_grad():
                perturbed_data.data = data + perturbed_data.uniform_(
                    -1 * self.epsilon, self.epsilon)
                perturbed_data.data.clamp_(d_min, d_max)

        for _ in range(k):

            data_grad = 0
            for _ in range(eot):
                output = model(perturbed_data)
                loss = F.cross_entropy(output, target)

                if perturbed_data.grad is not None:
                    perturbed_data.grad.data.zero_()

                loss.backward()
                data_grad += perturbed_data.grad.data
            data_grad /= eot

            with torch.no_grad():
                perturbed_data.data += a * torch.sign(data_grad)
                perturbed_data.data = torch.max(
                    torch.min(perturbed_data, data_max),
                    data_min)
        perturbed_data.requires_grad = False

        return perturbed_data

    def cw(self, net, input_v, label_v, c=0.01, gradient_iters=1, untarget=True,
           n_class=10, attack_iters=200, channel='empty', noise_epsilon=0):
        opt = Object()
        opt.gradient_iters = gradient_iters
        opt.attack_iters = attack_iters
        opt.channel = channel
        opt.noise_epsilon = noise_epsilon
        opt.ensemble = 1
        opt.limit_batch_number = 0

        return attack_cw(net=net, input_v=input_v, label_v=label_v, c=c,
                         untarget=untarget, n_class=n_class, opt=opt)

    def boundary_attack(self, net, input_v, label_v, steps=25000):
        net.eval()
        fmodel = foolbox.models.PyTorchModel(net, bounds=(0, 1))
        max_int = sys.maxsize
        attack = foolbox.attacks.BoundaryAttack(
            steps=steps,
            init_attack=foolbox.attacks.LinearSearchBlendedUniformNoiseAttack(directions=max_int, steps=1000),
            # init_attack=foolbox.attacks.BlendedUniformNoiseOnlyAttack(directions=max_int)
        )
        # we skip the second returned value which is the input, and the last one which is success rate
        advs, _, success_adv = attack(fmodel, input_v, label_v, epsilons=None)
        # print('successful adversaries: ', success_adv)
        return advs

    def spsa_attack(self, net, input_v, label_v=None, steps=1000):
        net.eval()
        advs = spsa(model_fn=net, x=input_v, eps=self.epsilon,
                    nb_iter=steps, norm=np.inf, clip_min=0, clip_max=1,
                    y=None,
                    targeted=False, early_stop_loss_threshold=None, learning_rate=0.01, delta=0.01,
                    spsa_samples=128, spsa_iters=1, is_debug=False, sanity_checks=False)
        return advs


def pgd_adapter(input_v, label_v, net, c, opt=None):
    k = opt.attack_iters
    eot = opt.eot
    return Attack(dataloader=None, epsilon=c).pgd(
        model=net, data=input_v, target=label_v, a=0.01, k=k,
        eot=eot
    )


def boundary_attack_adapter(input_v, label_v, net, c=None, opt=None):
    steps = opt.attack_iters
    return Attack(dataloader=None, epsilon=c).boundary_attack(net=net, input_v=input_v, label_v=label_v, steps=steps)


def spsa_attack_adapter(input_v, label_v, net, c=None, opt=None):
    steps = opt.attack_iters
    return Attack(dataloader=None, epsilon=c).spsa_attack(net=net, input_v=input_v, label_v=label_v, steps=steps)
