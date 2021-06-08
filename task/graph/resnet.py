import torch.nn as nn


class BasicBlock(nn.Module):
    expansion = 1

    def __init__(self, _in, _out, stride=1):
        super(BasicBlock, self).__init__()
        self.conv1 = nn.Conv2d(
            _in, _out, kernel_size=3, stride=stride, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(_out)
        self.conv2 = nn.Conv2d(_out, _out, kernel_size=3,
                               stride=1, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(_out)

        self.shortcut = nn.Sequential()
        if stride != 1 or _in != self.expansion*_out:
            self.shortcut = nn.Sequential(
                nn.Conv2d(_in, self.expansion*_out,
                          kernel_size=1, stride=stride, bias=False),
                nn.BatchNorm2d(self.expansion*_out)
            )

        self.relu = nn.ReLU(inplace=True)

    def forward(self, x):
        out = self.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        out += self.shortcut(x)
        out = self.relu(out)
        return out


class Bottleneck(nn.Module):
    expansion = 4

    def __init__(self, _in, _out, stride=1):
        super(Bottleneck, self).__init__()
        self.conv1 = nn.Conv2d(_in, _out, kernel_size=1, bias=False)
        self.bn1 = nn.BatchNorm2d(_out)
        self.conv2 = nn.Conv2d(_out, _out, kernel_size=3,
                               stride=stride, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(_out)
        self.conv3 = nn.Conv2d(_out, self.expansion *
                               _out, kernel_size=1, bias=False)
        self.bn3 = nn.BatchNorm2d(self.expansion*_out)

        self.shortcut = nn.Sequential()
        if stride != 1 or _in != self.expansion*_out:
            self.shortcut = nn.Sequential(
                nn.Conv2d(_in, self.expansion*_out,
                          kernel_size=1, stride=stride, bias=False),
                nn.BatchNorm2d(self.expansion*_out)
            )

        self.relu = nn.ReLU(inplace=True)

    def forward(self, x):
        out = self.relu(self.bn1(self.conv1(x)))
        out = self.relu(self.bn2(self.conv2(out)))
        out = self.bn3(self.conv3(out))
        out += self.shortcut(x)
        out = self.relu(out)
        return out


class ResNet(nn.Module):
    def __init__(self, block, num_blocks, num_classes=10):
        super(ResNet, self).__init__()
        self.in_planes = 64

        self.conv1 = nn.Conv2d(3, 64, kernel_size=3,
                               stride=1, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(64)
        self.layer1 = self._make_layer(block, 64, num_blocks[0], stride=1)
        self.layer2 = self._make_layer(block, 128, num_blocks[1], stride=2)
        self.layer3 = self._make_layer(block, 256, num_blocks[2], stride=2)
        self.layer4 = self._make_layer(block, 512, num_blocks[3], stride=2)
        self.linear = nn.Linear(512*block.expansion, num_classes)

        self.avg_pool = nn.AdaptiveAvgPool2d(512*block.expansion)

    def _make_layer(self, block, planes, num_blocks, stride):
        strides = [stride] + [1]*(num_blocks-1)
        layers = []
        for stride in strides:
            layers.append(block(self.in_planes, planes, stride))
            self.in_planes = planes * block.expansion
        return nn.Sequential(*layers)

    def forward(self, x):
        out = self.relu(self.bn1(self.conv1(x)))
        out = self.layer1(out)
        out = self.layer2(out)
        out = self.layer3(out)
        out = self.layer4(out)

        out = self.avg_pool(out)
        out = out.view(out.size(0), -1)
        out = self.linear(out)

        return out


def ResNet18():
    return ResNet(BasicBlock, [2, 2, 2, 2])


def ResNet34():
    return ResNet(BasicBlock, [3, 4, 6, 3])


def ResNet50():
    return ResNet(Bottleneck, [3, 4, 6, 3])


def ResNet101():
    return ResNet(Bottleneck, [3, 4, 23, 3])


def ResNet152():
    return ResNet(Bottleneck, [3, 8, 36, 3])


class Loss(nn.Module):
    def __init__(self):
        super().__init__()

        self.loss = nn.CrossEntropyLoss()

    def forward(self, logit, target, num_classes):
        target = nn.functional.one_hot(target, num_classes)
        return self.loss(logit, target)