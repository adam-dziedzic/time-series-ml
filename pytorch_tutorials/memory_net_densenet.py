from collections import OrderedDict

import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.utils.model_zoo as model_zoo

from cnns.nnlib.pytorch_layers.spectral_conv_2d import SpectralConv2d
from cnns.nnlib.utils.general_utils import ConvType

__all__ = ['DenseNet', 'densenet121', 'densenet169', 'densenet201',
           'densenet161']

model_urls = {
    'densenet121': 'https://download.pytorch.org/models/densenet121-241335ed.pth',
    'densenet169': 'https://download.pytorch.org/models/densenet169-6f0f7f60.pth',
    'densenet201': 'https://download.pytorch.org/models/densenet201-4c113574.pth',
    'densenet161': 'https://download.pytorch.org/models/densenet161-17b70270.pth',
}


def densenet121(pretrained=False, **kwargs):
    r"""Densenet-121 model from
    `"Densely Connected Convolutional Networks" <https://arxiv.org/pdf/1608.06993.pdf>`

    Arguments:
        pretrained (bool): If True, returns a model pre-trained on ImageNet
    """
    model = DenseNet(num_init_features=64, growth_rate=32,
                     block_config=(6, 12, 24, 16), **kwargs)
    if pretrained:
        model.load_state_dict(model_zoo.load_url(model_urls['densenet121']))
    return model


def densenet169(pretrained=False, **kwargs):
    r"""Densenet-169 model from
    `"Densely Connected Convolutional Networks" <https://arxiv.org/pdf/1608.06993.pdf>`

    Arguments:
        pretrained (bool): If True, returns a model pre-trained on ImageNet
    """
    model = DenseNet(num_init_features=64, growth_rate=32,
                     block_config=(6, 12, 32, 32), **kwargs)
    if pretrained:
        model.load_state_dict(model_zoo.load_url(model_urls['densenet169']))
    return model


def densenet201(pretrained=False, **kwargs):
    r"""Densenet-201 model from
    `"Densely Connected Convolutional Networks" <https://arxiv.org/pdf/1608.06993.pdf>`

    Arguments:
        pretrained (bool): If True, returns a model pre-trained on ImageNet
    """
    model = DenseNet(num_init_features=64, growth_rate=32,
                     block_config=(6, 12, 48, 32), **kwargs)
    if pretrained:
        model.load_state_dict(model_zoo.load_url(model_urls['densenet201']))
    return model


def densenet161(pretrained=False, **kwargs):
    r"""Densenet-201 model from
    `"Densely Connected Convolutional Networks" <https://arxiv.org/pdf/1608.06993.pdf>`

    Arguments:
        pretrained (bool): If True, returns a model pre-trained on ImageNet
    """
    model = DenseNet(num_init_features=96, growth_rate=48,
                     block_config=(6, 12, 36, 24), **kwargs)
    if pretrained:
        model.load_state_dict(model_zoo.load_url(model_urls['densenet161']))
    return model


class _DenseLayer(nn.Sequential):
    def __init__(self, num_input_features, growth_rate, bn_size, drop_rate,
                 conv_type):
        super(_DenseLayer, self).__init__()
        self.add_module('norm1', nn.BatchNorm2d(num_input_features))
        self.add_module('relu1', nn.ReLU(inplace=True))
        if conv_type is ConvType.SPECTRAL_PARAM:
            conv1 = SpectralConv2d(num_input_features, bn_size * growth_rate,
                                   kernel_size=1, stride=1, bias=False)
        else:
            conv1 = nn.Conv2d(num_input_features, bn_size * growth_rate,
                              kernel_size=1, stride=1, bias=False)
        self.add_module('conv1', conv1)
        self.add_module('norm2', nn.BatchNorm2d(bn_size * growth_rate))
        self.add_module('relu2', nn.ReLU(inplace=True))
        if conv_type is ConvType.SPECTRAL_PARAM:
            conv2 = SpectralConv2d(bn_size * growth_rate, growth_rate,
                                   kernel_size=3, stride=1, padding=1,
                                   bias=False)
        else:
            conv2 = nn.Conv2d(bn_size * growth_rate, growth_rate, kernel_size=3,
                              stride=1, padding=1, bias=False)
        self.add_module('conv2', conv2)
        self.drop_rate = drop_rate

    def forward(self, x):
        new_features = super(_DenseLayer, self).forward(x)
        if self.drop_rate > 0:
            new_features = F.dropout(new_features, p=self.drop_rate,
                                     training=self.training)
        return torch.cat([x, new_features], 1)


class _DenseBlock(nn.Sequential):
    def __init__(self, num_layers, num_input_features, bn_size, growth_rate,
                 drop_rate, conv_type):
        super(_DenseBlock, self).__init__()
        for i in range(num_layers):
            layer = _DenseLayer(num_input_features + i * growth_rate,
                                growth_rate, bn_size, drop_rate, conv_type)
            self.add_module('denselayer%d' % (i + 1), layer)


class _Transition(nn.Sequential):
    def __init__(self, num_input_features, num_output_features, conv_type):
        super(_Transition, self).__init__()
        self.add_module('norm', nn.BatchNorm2d(num_input_features))
        self.add_module('relu', nn.ReLU(inplace=True))
        if conv_type is ConvType.SPECTRAL_PARAM:
            conv = SpectralConv2d(num_input_features, num_output_features,
                                  kernel_size=1, stride=1, bias=False)
        else:
            conv = nn.Conv2d(num_input_features, num_output_features,
                             kernel_size=1, stride=1, bias=False)
        self.add_module('conv', conv)
        self.add_module('pool', nn.AvgPool2d(kernel_size=2, stride=2))


class DenseNet(nn.Module):
    r"""Densenet-BC model class, based on
    `"Densely Connected Convolutional Networks"
    <https://arxiv.org/pdf/1608.06993.pdf>`

    Arguments:
        growth_rate (int) - how many filters to add each layer (`k` in paper)
        block_config (list of 4 ints) - how many layers in each pooling block
        num_init_features (int) - the number of filters to learn in the first
        convolution layer
        bn_size (int) - multiplicative factor for number of bottle neck layers
          (i.e. bn_size * k features in the bottleneck layer)
        drop_rate (float) - dropout rate after each dense layer
        num_classes (int) - number of classification classes
    """

    def __init__(self, growth_rate=32, block_config=(6, 12, 24, 16),
                 num_init_features=64, bn_size=4, drop_rate=0, num_classes=10,
                 input_channel=3, conv_type=ConvType.SPECTRAL_PARAM,
                 small_inputs=True):

        super(DenseNet, self).__init__()

        if small_inputs:
            if conv_type is ConvType.SPECTRAL_PARAM:
                conv = SpectralConv2d(in_channels=3,
                                      out_channels=num_init_features,
                                      kernel_size=3,
                                      stride=1, padding=1, bias=False)
            else:
                conv = nn.Conv2d(in_channels=3, out_channels=num_init_features,
                                 kernel_size=3, stride=1,
                                 padding=1, bias=False)

            self.features = nn.Sequential(OrderedDict([('conv0', conv), ]))
        else:
            if conv_type is ConvType.SPECTRAL_PARAM:
                conv = SpectralConv2d(
                    in_channels=3, out_channels=num_init_features,
                    kernel_size=7,
                    stride=2, padding=3, bias=False)
            else:
                conv = nn.Conv2d(in_channels=3,
                                 out_channels=num_init_features,
                                 kernel_size=7, stride=2, padding=3,
                                 bias=False)
            # First convolution
            self.features = nn.Sequential(OrderedDict([
                ('conv0', conv),
                ('norm0', nn.BatchNorm2d(num_init_features)),
                ('relu0', nn.ReLU(inplace=True)),
                ('pool0', nn.MaxPool2d(kernel_size=3, stride=2, padding=1)),
            ]))

        # Each denseblock
        num_features = num_init_features
        for i, num_layers in enumerate(block_config):
            block = _DenseBlock(num_layers=num_layers,
                                num_input_features=num_features,
                                bn_size=bn_size,
                                growth_rate=growth_rate,
                                drop_rate=drop_rate,
                                conv_type=conv_type)
        self.features.add_module('denseblock%d' % (i + 1), block)
        num_features = num_features + num_layers * growth_rate
        if i != len(block_config) - 1:
            trans = _Transition(num_input_features=num_features,
                                num_output_features=num_features // 2,
                                conv_type=conv_type)
        self.features.add_module('transition%d' % (i + 1), trans)
        num_features = num_features // 2

        # Final batch norm
        self.features.add_module('norm5', nn.BatchNorm2d(num_features))

        # Linear layer
        self.classifier = nn.Linear(num_features, num_classes)

        self.input_channel = input_channel

    def forward(self, x):
        features = self.features(x)
        out = F.relu(features, inplace=True)
        if out.shape[-1] >= 7:
            out = F.avg_pool2d(out, kernel_size=7).view(features.size(0), -1)
        else:
            out = out.view(features.size(0), -1)
        out = self.classifier(out)
        return out
